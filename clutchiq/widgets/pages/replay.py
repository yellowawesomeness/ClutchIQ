"""Premium replay workspace."""
from __future__ import annotations
from math import cos,sin,radians
from typing import Callable
from PySide6.QtCore import QTimer,Qt,QSize,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QBrush
from PySide6.QtWidgets import QLabel,QPushButton,QSlider,QVBoxLayout,QHBoxLayout,QFrame,QWidget,QSizePolicy
from clutchiq.replay_radar import DEFAULT_RADAR_REGISTRY,RadarMapRegistry
from clutchiq.replay_state.models import ReplayViewModel
class RadarView(QWidget):
 def __init__(self,registry:RadarMapRegistry=DEFAULT_RADAR_REGISTRY,parent=None):
  super().__init__(parent);self._registry=registry;self._view_model=self._spatial=None;self._current_tick=None;self._map_spec=self._map_pixmap=None;self.setMinimumSize(QSize(480,390));self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
 def set_replay(self,v,s,t):
  self._view_model,self._spatial,self._current_tick=v,s,t;spec=self._registry.resolve(getattr(getattr(v.record,'analysis_summary',None),'map_name',None) if v else None)
  if spec is not self._map_spec:self._map_spec,self._map_pixmap=spec,(self._registry.load_pixmap(spec) if spec else None)
  self.update()
 def paintEvent(self,e):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.fillRect(self.rect(),QColor('#11151d'));r=self.rect().adjusted(16,16,-16,-16);p.setPen(QPen(QColor('#2a3444'),1));p.setBrush(QBrush(QColor('#161d28')));p.drawRoundedRect(r,16,16)
  if not self._map_spec or not self._map_pixmap:p.setPen(QColor('#8f9bad'));p.drawText(r,Qt.AlignCenter,'Radar unavailable');return
  p.save();p.setClipRect(r);p.drawPixmap(r,self._map_pixmap)
  if self._spatial is not None and self._current_tick is not None:
   pts=[]
   for _,z in self._spatial.rows_at_tick(self._current_tick)[lambda x:x['is_alive']].iterrows():
    q=self._map_spec.normalized(float(z['X']),float(z['Y']))
    if q:pts.append((z,r.left()+q[0]*r.width(),r.top()+q[1]*r.height()))
   for i,(a,x,y) in enumerate(pts):
    for b,u,v in pts[i+1:]:
     if a['team_name']!=b['team_name'] and ((x-u)**2+(y-v)**2)**.5<150:p.setPen(QPen(QColor('#f4c430'),2,Qt.DashLine));p.drawLine(int(x),int(y),int(u),int(v))
   for z,x,y in pts:
    c=QColor('#64b5f6' if str(z['team_name']).upper().startswith('CT') else '#ff765c');a=radians(float(z['yaw']));p.setPen(QPen(c,2));p.drawLine(int(x),int(y),int(x+cos(a)*25),int(y-sin(a)*25));p.setBrush(QBrush(c));p.drawEllipse(int(x)-7,int(y)-7,14,14);p.setPen(QColor('white'));p.drawText(int(x)+10,int(y)-10,str(z['name'])[:12])
  p.restore()
class KillTimelineView(QWidget):
 seek_requested=Signal(int)
 def __init__(self,p=None):super().__init__(p);self._events=();self._start_tick=self._end_tick=self._current_tick=None;self.setMinimumHeight(64)
 def set_timeline(self,a,b,c,d):self._events,self._start_tick,self._end_tick,self._current_tick=a,b,c,d;self.update()
 def paintEvent(self,e):
  p=QPainter(self);p.fillRect(self.rect(),QColor('#161d28'));y=self.height()//2;p.setPen(QPen(QColor('#344156'),2));p.drawLine(18,y,self.width()-18,y)
  if self._start_tick is None or self._end_tick is None or self._end_tick<=self._start_tick:return
  for x in self._events:
   q=18+(x.tick-self._start_tick)/(self._end_tick-self._start_tick)*(self.width()-36);p.setBrush(QBrush(QColor('#f4c430')));p.drawEllipse(int(q)-5,y-5,10,10)
class ReplayPage(QWidget):
 def __init__(self,back_callback:Callable[[],None]|None=None,parent=None):
  super().__init__(parent);self.setObjectName('replayPage');self._back_callback=back_callback;self._view_model=self._spatial=None;self._kill_events=();self._current_tick=None;self._is_playing=False;self._timer=QTimer(self);self._timer.timeout.connect(self._step_forward);self.setStyleSheet("QWidget#replayPage{background:#0d1118;color:#e8eef9}QFrame{background:#161d28;border:1px solid #2a3444;border-radius:14px}QPushButton{background:#202a38;border:1px solid #344156;border-radius:8px;color:#e8eef9;min-height:32px;padding:0 14px}QPushButton#play{background:#f4c430;color:#10151d;min-width:86px}QSlider::groove:horizontal{height:4px;background:#344156}QSlider::sub-page:horizontal{background:#f4c430}QSlider::handle:horizontal{width:14px;margin:-5px 0;border-radius:7px;background:#fff}")
  l=QVBoxLayout(self);l.setContentsMargins(28,24,28,28);l.setSpacing(16);h=QFrame();q=QHBoxLayout(h);copy=QVBoxLayout();self._round_label=QLabel('REPLAY / COACHING REVIEW');self._metadata_label=QLabel('No replay loaded.');copy.addWidget(self._round_label);copy.addWidget(self._metadata_label);q.addLayout(copy);q.addStretch();self._back_button=QPushButton('Back to Match Details');self._back_button.clicked.connect(self._handle_back);q.addWidget(self._back_button);l.addWidget(h)
  s=QFrame();q=QHBoxLayout(s);self._score_ct_label=QLabel();self._score_t_label=QLabel();self._winner_label=QLabel();self._start_tick_label=QLabel();[q.addWidget(x) for x in (self._score_ct_label,self._score_t_label,self._winner_label,self._start_tick_label)];q.addStretch();l.addWidget(s)
  f=QFrame();q=QVBoxLayout(f);self._radar_view=RadarView();q.addWidget(self._radar_view);l.addWidget(f,1);f=QFrame();q=QVBoxLayout(f);head=QHBoxLayout();self._kill_label=QLabel('Kills: 0 / 0');self._tick_label=QLabel();head.addWidget(self._kill_label);head.addStretch();head.addWidget(self._tick_label);q.addLayout(head);self._kill_timeline_view=KillTimelineView();q.addWidget(self._kill_timeline_view);self._slider=QSlider(Qt.Horizontal);self._slider.valueChanged.connect(self._set_tick);q.addWidget(self._slider);l.addWidget(f)
  f=QFrame();q=QHBoxLayout(f);q.addStretch();self._step_back_button=QPushButton('‹');self._step_back_button.clicked.connect(self._step_back);self._play_button=QPushButton('Play');self._play_button.setObjectName('play');self._play_button.clicked.connect(self._toggle_playback);self._step_forward_button=QPushButton('›');self._step_forward_button.clicked.connect(self._step_forward);[q.addWidget(x) for x in (self._step_back_button,self._play_button,self._step_forward_button)];q.addStretch();l.addWidget(f)
 def set_round(self,record,round_,back_callback,kill_events=()):self.set_view_model(ReplayViewModel(record=record,round=round_),back_callback,kill_events)
 def set_view_model(self,v,back_callback,kill_events=()):self._view_model,self._back_callback=v,back_callback;self._kill_events=tuple(e for e in kill_events if e.kind=='kill.recorded' and e.round_number==v.round_number and (v.start_tick is None or e.tick>=v.start_tick) and (v.end_tick is None or e.tick<=v.end_tick));self._current_tick=v.start_tick or v.end_tick;self._refresh()
 def set_spatial_data(self,s):self._spatial=s;self._refresh()
 def _handle_back(self):
  if self._back_callback is not None:self._back_callback()
 def _tick(self):return self._current_tick or 0
 def _refresh(self):
  if not self._view_model:return
  v=self._view_model;self._metadata_label.setText(f'Match: {v.source_name}');self._score_ct_label.setText(f'CT {v.score_ct}');self._score_t_label.setText(f'T {v.score_t}');self._winner_label.setText(f'WINNER {v.winner_team}');self._start_tick_label.setText(f'Start tick: {v.start_tick}');self._radar_view.set_replay(v,self._spatial,self._tick());self._kill_timeline_view.set_timeline(self._kill_events,v.start_tick,v.end_tick,self._tick());self._kill_label.setText(f'Kills: {sum(e.tick<=self._tick() for e in self._kill_events)} / {len(self._kill_events)}');self._tick_label.setText(f'Tick: {self._tick()}');self._slider.setRange(v.start_tick or 0,v.end_tick or 0);self._slider.blockSignals(True);self._slider.setValue(self._tick());self._slider.blockSignals(False)
 def _set_tick(self,x):
  if self._view_model:self._current_tick=max(self._view_model.start_tick or x,min(self._view_model.end_tick or x,x));self._refresh()
 def _toggle_playback(self):self._is_playing=not self._is_playing;self._timer.start(250) if self._is_playing else self._timer.stop();self._play_button.setText('Pause' if self._is_playing else 'Play')
 def _step_back(self):self._set_tick(self._tick()-1)
 def _step_forward(self):self._set_tick(self._tick()+1)
