"""Premium replay workspace."""
from __future__ import annotations
from math import cos,sin,radians
from typing import Callable
from PySide6.QtCore import QTimer,Qt,QSize,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QBrush
from PySide6.QtWidgets import QLabel,QPushButton,QSlider,QVBoxLayout,QHBoxLayout,QFrame,QWidget
from clutchiq.replay_radar import DEFAULT_RADAR_REGISTRY,RadarMapRegistry
from clutchiq.replay_state.models import ReplayViewModel
class RadarView(QWidget):
 def __init__(self,registry:RadarMapRegistry=DEFAULT_RADAR_REGISTRY,parent=None):super().__init__(parent);self._registry=registry;self._view_model=self._spatial=None;self._current_tick=None;self._map_spec=self._map_pixmap=None;self.setMinimumSize(QSize(620,520))
 def set_replay(self,v,s,t):
  self._view_model,self._spatial,self._current_tick=v,s,t;spec=self._registry.resolve(getattr(getattr(v.record,'analysis_summary',None),'map_name',None) if v else None)
  if spec is not self._map_spec:self._map_spec,self._map_pixmap=spec,(self._registry.load_pixmap(spec) if spec else None)
  self.update()
 def paintEvent(self,e):
  p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#0D0D0D'));r=self.rect().adjusted(18,18,-18,-18);p.setPen(QPen(QColor('#343434'),1));p.setBrush(QBrush(QColor('#151515')));p.drawRoundedRect(r,18,18)
  if not self._map_spec or not self._map_pixmap:p.setPen(QColor('#999'));p.drawText(r,Qt.AlignmentFlag.AlignCenter,'Radar unavailable');return
  p.save();p.setClipRect(r);p.drawPixmap(r,self._map_pixmap)
  if self._spatial is not None and self._current_tick is not None:
   rows=self._spatial.rows_at_tick(self._current_tick);pts=[]
   for _,z in rows[rows['is_alive']].iterrows():
    q=self._map_spec.normalized(float(z['X']),float(z['Y']))
    if q:pts.append((z,r.left()+q[0]*r.width(),r.top()+q[1]*r.height()))
   for i,(a,x,y) in enumerate(pts):
    for b,u,v in pts[i+1:]:
     if a['team_name']!=b['team_name'] and ((x-u)**2+(y-v)**2)**.5<150:p.setPen(QPen(QColor('#F4C430'),2,Qt.PenStyle.DashLine));p.drawLine(int(x),int(y),int(u),int(v))
   for z,x,y in pts:
    c=QColor('#64B5F6' if str(z['team_name']).upper().startswith('CT') else '#FF765C');a=radians(float(z['yaw']));p.setPen(QPen(c,2));p.drawLine(int(x),int(y),int(x+cos(a)*25),int(y-sin(a)*25));p.setBrush(QBrush(c));p.drawEllipse(int(x)-7,int(y)-7,14,14);p.setPen(QColor('white'));p.drawText(int(x)+10,int(y)-10,str(z['name'])[:12])
  p.restore()
class KillTimelineView(QWidget):
 seek_requested=Signal(int)
 def __init__(self,p=None):super().__init__(p);self._events=();self._start_tick=self._end_tick=self._current_tick=None;self.setMinimumHeight(56)
 def set_timeline(self,a,b,c,d):self._events,self._start_tick,self._end_tick,self._current_tick=a,b,c,d;self.update()
 def paintEvent(self,e):
  p=QPainter(self);p.fillRect(self.rect(),QColor('#0D0D0D'));y=self.height()//2;p.setPen(QPen(QColor('#383838'),2));p.drawLine(14,y,self.width()-14,y)
  if self._start_tick is None or not self._end_tick:return
  for x in self._events:
   q=14+(x.tick-self._start_tick)/(self._end_tick-self._start_tick)*(self.width()-28);p.setBrush(QBrush(QColor('#F4C430')));p.drawEllipse(int(q)-5,y-5,10,10)
class ReplayPage(QWidget):
 def __init__(self,back_callback:Callable[[],None]|None=None,parent=None):
  super().__init__(parent);self._back_callback=back_callback;self._view_model=self._spatial=None;self._kill_events=();self._current_tick=None;self._is_playing=False;self._timer=QTimer(self);self._timer.timeout.connect(self._step_forward);l=QVBoxLayout(self);self._metadata_label=QLabel('No replay loaded.');self._round_label=QLabel('REPLAY / COACHING REVIEW');l.addWidget(self._round_label);l.addWidget(self._metadata_label);self._back_button=QPushButton('Back to Match Details');self._back_button.clicked.connect(self._handle_back);l.addWidget(self._back_button);self._score_ct_label=QLabel();self._score_t_label=QLabel();self._winner_label=QLabel();self._start_tick_label=QLabel();[l.addWidget(x) for x in (self._score_ct_label,self._score_t_label,self._winner_label,self._start_tick_label)];f=QFrame();q=QVBoxLayout(f);self._radar_view=RadarView();q.addWidget(self._radar_view);l.addWidget(f);self._kill_timeline_view=KillTimelineView();l.addWidget(self._kill_timeline_view);self._kill_label=QLabel('Kills: 0 / 0');l.addWidget(self._kill_label);self._tick_label=QLabel();self._slider=QSlider(Qt.Orientation.Horizontal);self._slider.valueChanged.connect(self._set_tick);l.addWidget(self._tick_label);l.addWidget(self._slider);self._play_button=QPushButton('Play');self._play_button.clicked.connect(self._toggle_playback);self._step_back_button=QPushButton('‹');self._step_back_button.clicked.connect(self._step_back);self._step_forward_button=QPushButton('›');self._step_forward_button.clicked.connect(self._step_forward);[l.addWidget(x) for x in (self._play_button,self._step_back_button,self._step_forward_button)]
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
