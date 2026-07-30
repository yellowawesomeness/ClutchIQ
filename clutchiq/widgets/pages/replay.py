"""Read-only replay page."""
from __future__ import annotations
from typing import Callable
import pandas as pd
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from clutchiq.replay_radar import DEFAULT_RADAR_REGISTRY, RadarMapRegistry, RadarMapSpec
from clutchiq.replay_state.models import ReplayViewModel
from clutchiq.replay_state.spatial import SpatialReplayData
from clutchiq.timeline_engine.models import TimelineEvent
from clutchiq.widgets.components import AppCard, AppEyebrow, AppSubtitle, AppTitle

class RadarView(QWidget):
    def __init__(self, registry: RadarMapRegistry = DEFAULT_RADAR_REGISTRY, parent=None):
        super().__init__(parent); self._registry=registry; self._view_model=self._spatial=None; self._current_tick=None; self._map_spec=None; self._map_pixmap=None; self.setMinimumSize(QSize(480,480))
    def set_replay(self, view_model, spatial, current_tick):
        self._view_model,self._spatial,self._current_tick=view_model,spatial,current_tick
        name=getattr(getattr(view_model.record,"analysis_summary",None),"map_name",None) if view_model else None
        self._map_spec=self._registry.resolve(name); self._map_pixmap=self._registry.load_pixmap(self._map_spec) if self._map_spec else None; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.fillRect(self.rect(),QColor("#111827")); p.setRenderHint(QPainter.RenderHint.Antialiasing); rect=self.rect().adjusted(12,12,-12,-12); p.setPen(QPen(QColor("#334155"),2)); p.setBrush(QBrush(QColor("#0f172a"))); p.drawRoundedRect(rect,12,12)
        if self._map_spec is None or self._map_pixmap is None: p.setPen(QColor("#94a3b8")); p.drawText(rect,Qt.AlignmentFlag.AlignCenter,"Radar unavailable"); return
        p.drawPixmap(rect,self._map_pixmap)
        if self._spatial is None or self._current_tick is None or self._spatial.rows_at_tick(self._current_tick).empty: p.setPen(QColor("#94a3b8")); p.drawText(rect,Qt.AlignmentFlag.AlignCenter,"No spatial data available"); return
        for _,row in self._spatial.rows_at_tick(self._current_tick).iterrows():
            point=self._map_spec.normalized(float(row["X"]),float(row["Y"]))
            if point is None: continue
            x,y=rect.left()+point[0]*rect.width(),rect.top()+point[1]*rect.height(); p.setBrush(QBrush(QColor("#38bdf8" if str(row["team_name"]).upper().startswith("CT") else "#f97316"))); p.setPen(QPen(QColor("white"),1)); p.drawEllipse(int(x)-6,int(y)-6,12,12); p.setPen(QColor("white")); p.drawText(int(x)+8,int(y)-8,str(row["name"])[:12])

class KillTimelineView(QWidget):
    def __init__(self,parent=None): super().__init__(parent); self._events=(); self._start_tick=self._end_tick=self._current_tick=None; self.setMinimumHeight(48)
    def set_timeline(self,events,start_tick,end_tick,current_tick): self._events,self._start_tick,self._end_tick,self._current_tick=events,start_tick,end_tick,current_tick; self.update()
    def paintEvent(self,event):
        p=QPainter(self); r=self.rect().adjusted(10,12,-10,-12); p.fillRect(self.rect(),QColor("#111827")); p.setPen(QPen(QColor("#475569"),2)); p.drawLine(r.left(),r.center().y(),r.right(),r.center().y())
        if self._start_tick is None or self._end_tick is None or self._end_tick<=self._start_tick:return
        for kill in self._events:
            x=r.left()+(kill.tick-self._start_tick)/(self._end_tick-self._start_tick)*r.width(); p.setBrush(QBrush(QColor("#ef4444") if self._current_tick is None or kill.tick>self._current_tick else QColor("#fbbf24"))); p.setPen(QPen(QColor("#f8fafc"),1)); p.drawEllipse(int(x)-5,r.center().y()-5,10,10)

class ReplayPage(QWidget):
    def __init__(self,back_callback:Callable[[],None]|None=None,parent=None):
        super().__init__(parent); self._back_callback=back_callback; self._view_model=self._spatial=None; self._kill_events=(); self._current_tick=None; self._is_playing=False; self._timer=QTimer(self); self._timer.setInterval(250); self._timer.timeout.connect(self._step_forward); layout=QVBoxLayout(self); layout.addWidget(AppEyebrow("REPLAY WORKSPACE")); layout.addWidget(AppTitle("Replay")); layout.addWidget(AppSubtitle("Round playback with radar map, scrub, step controls, and kill timeline.")); self._card=AppCard(); self._card_layout=QVBoxLayout(self._card)
        self._metadata_label=QLabel("No replay loaded."); self._round_label=QLabel(); self._start_label=QLabel(); self._end_label=QLabel(); self._score_ct_label=QLabel(); self._score_t_label=QLabel(); self._winner_label=QLabel(); self._kill_label=QLabel("Kills: 0")
        for w in (self._metadata_label,self._round_label,self._start_label,self._end_label,self._score_ct_label,self._score_t_label,self._winner_label,self._kill_label):self._card_layout.addWidget(w)
        self._radar_view=RadarView(); self._kill_timeline_view=KillTimelineView(); self._tick_label=QLabel("Tick: Unknown"); self._slider=QSlider(Qt.Orientation.Horizontal); self._slider.valueChanged.connect(self._on_slider_changed); self._play_button=QPushButton("Play"); self._play_button.clicked.connect(self._toggle_playback); self._step_back_button=QPushButton("Step Back"); self._step_back_button.clicked.connect(self._step_back); self._step_forward_button=QPushButton("Step Forward"); self._step_forward_button.clicked.connect(self._step_forward); self._back_button=QPushButton("Back to Match Details"); self._back_button.clicked.connect(self._on_back)
        for w in (self._radar_view,self._kill_timeline_view,self._tick_label,self._slider,self._play_button,self._step_back_button,self._step_forward_button,self._back_button):self._card_layout.addWidget(w)
        layout.addWidget(self._card); layout.addStretch(1); self._sync_navigation_controls()
    def set_round(self,record,round_,back_callback,kill_events=()): self.set_view_model(ReplayViewModel(record=record,round=round_),back_callback,kill_events)
    def set_view_model(self,view_model,back_callback,kill_events=()): self._view_model,self._back_callback=view_model,back_callback; self._kill_events=tuple(e for e in kill_events if e.kind=="kill.recorded" and e.round_number==view_model.round_number and self._in_round(e.tick)); self._current_tick=view_model.start_tick if view_model.start_tick is not None else view_model.end_tick; self._is_playing=False; self._timer.stop(); self._refresh()
    def set_spatial_data(self,spatial): self._spatial=spatial; self._refresh()
    def _in_round(self,tick): return self._view_model is not None and (self._view_model.start_tick is None or tick>=self._view_model.start_tick) and (self._view_model.end_tick is None or tick<=self._view_model.end_tick)
    def _refresh(self):
        if self._view_model is None: self._metadata_label.setText("No replay loaded."); self._radar_view.set_replay(None,None,None); self._kill_timeline_view.set_timeline((),None,None,None)
        else:
            v=self._view_model; self._metadata_label.setText(f"Match: {v.source_name}"); self._round_label.setText(f"Round: {v.round_number}"); self._start_label.setText(f"Start tick: {self._format_value(v.start_tick)}"); self._end_label.setText(f"End tick: {self._format_value(v.end_tick)}"); self._score_ct_label.setText(f"CT score: {self._format_value(v.score_ct)}"); self._score_t_label.setText(f"T score: {self._format_value(v.score_t)}"); self._winner_label.setText(f"Winner: {self._format_value(v.winner_team)}"); self._radar_view.set_replay(v,self._spatial,self._normalized_tick()); self._sync_kill_timeline()
        self._sync_navigation_controls(); self._sync_tick_display()
    def _sync_kill_timeline(self): self._kill_label.setText(f"Kills: {sum(e.tick<=self._normalized_tick() for e in self._kill_events)} / {len(self._kill_events)}"); self._kill_timeline_view.set_timeline(self._kill_events,self._view_model.start_tick,self._view_model.end_tick,self._normalized_tick())
    def _format_value(self,v): return "Unknown" if v is None else str(v)
    def _toggle_playback(self):
        if self._view_model is None:return
        self._is_playing=not self._is_playing; self._timer.start() if self._is_playing else self._timer.stop(); self._sync_navigation_controls()
    def _step_back(self):
        if self._view_model is not None:self._set_tick(self._normalized_tick()-1)
    def _step_forward(self):
        if self._view_model is None:return
        if self._view_model.end_tick is not None and self._normalized_tick()>=self._view_model.end_tick:self._is_playing=False; self._timer.stop(); self._sync_navigation_controls(); return
        self._set_tick(self._normalized_tick()+1)
    def _normalized_tick(self): return self._current_tick if self._current_tick is not None else ((self._view_model.start_tick or self._view_model.end_tick or 0) if self._view_model else 0)
    def _set_tick(self,tick):
        if self._view_model is None:return
        low=self._view_model.start_tick if self._view_model.start_tick is not None else tick; high=self._view_model.end_tick if self._view_model.end_tick is not None else tick; self._current_tick=max(min(low,high),min(max(low,high),tick)); self._refresh()
    def _on_slider_changed(self,value): self._set_tick(value)
    def _sync_tick_display(self):
        if self._view_model is None:self._tick_label.setText("Tick: Unknown"); self._slider.setEnabled(False); return
        self._tick_label.setText(f"Tick: {self._normalized_tick()}"); start,end=self._view_model.start_tick,self._view_model.end_tick; self._slider.setEnabled(start is not None and end is not None)
        if start is not None and end is not None:self._slider.blockSignals(True); self._slider.setRange(start,end); self._slider.setValue(self._normalized_tick()); self._slider.blockSignals(False)
    def _sync_navigation_controls(self):
        enabled=self._view_model is not None; self._play_button.setEnabled(enabled); self._step_back_button.setEnabled(enabled); self._step_forward_button.setEnabled(enabled); self._play_button.setText("Pause" if self._is_playing else "Play")
    def _on_back(self):
        if self._back_callback:self._back_callback()
