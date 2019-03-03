'''
Mixin class to be inherited together with Pythonista ui.View for gesture support.

Implement following methods to handle gestures:
* on_tap
* on_pinch
* on_pan
'''

import time
import ui
from scene import Point

class GestureTouch:
  
  def __init__(self, location):
    self._location = location
    self.prev_location = location
    self.start_location = location
  
  @property
  def location(self):
    return self._location
    
  @location.setter
  def location(self, value):
    self.prev_location = self._location
    self._location = value
    
  @property
  def distance_from_start(self):
    return abs(Point(*self.location) - Point(*self.start_location))

class GestureData:
  
  tap_threshold = 0.3 # seconds
  long_press_threshold = 1 # second
  move_threshold = 20 # pixels
  
  BEGAN = 0
  MOVED = 1
  ENDED = 2
  COMPLETE = 3
  
  UP = 1
  DOWN = 2
  LEFT = 3
  RIGHT = 4
  
  def __init__(self):
    self.touches = {}
    self.no_of_touches = 0
    self.moving = False
    self.state = GestureData.BEGAN
    self.swipe_direction = None
    self.start_pinch_distance = None
    
  def complete(self):
    self.state = GestureData.COMPLETE
    
  def center_location(self):
    center_loc = Point(0,0)
    for touch in self.touches.values():
      center_loc += Point(*touch.location)
    center_loc /= len(self.touches)     
    return center_loc
    
  @property
  def pinch_distance(self):
    touches = list(self.touches.values())
    distance_vector = touches[0].location - touches[1].location
    return abs(distance_vector)
    

class GestureMixin():
  
  def touch_began(self, touch):
    if not hasattr(self, '_gestures') or len(self._gestures.touches) == 0:
      self._gestures = GestureData()
    g = self._gestures
    if len(g.touches) == 0:
      g.start_time = time.time()
      g.location = touch.location
    g.touches[touch.touch_id] = GestureTouch(touch.location)
    g.no_of_touches = max(g.no_of_touches, len(g.touches))
    if g.no_of_touches == 2:
      g.start_pinch_distance = g.pinch_distance
    
  def touch_moved(self, touch):
    g = self._gestures
    if g.state == GestureData.COMPLETE:
      return 
    t = g.touches[touch.touch_id]
    g.duration = time.time() - g.start_time
    t.location = touch.location
    g.location = g.center_location()
    
    if not g.moving:
      if t.distance_from_start > g.move_threshold:
        g.moving = True
    if not g.moving and g.duration > g.long_press_threshold and hasattr(self, 'on_long_press'):
      self.on_long_press(g)
      g.state = GestureData.COMPLETE

    if g.moving:
      g.state = GestureData.MOVED
      if (len(g.touches) == 1 and 
          g.duration < GestureData.tap_threshold and 
          hasattr(self, 'on_swipe')):
        g.swipe_direction = True
      else:
        g.swipe_direction = None
        if hasattr(self, 'on_pan'):
          self.on_pan(g)
        if len(g.touches) > 1:
          if len(g.touches) == 2 and hasattr(self, 'on_pinch'):
            g.scale = g.pinch_distance/g.start_pinch_distance
            self.on_pinch(g)
          

    if hasattr(self, 'on_debug'):
      self.on_debug(g)
    
  def touch_ended(self, touch):
    g = self._gestures
    del g.touches[touch.touch_id]
    if g.state == GestureData.COMPLETE:
      return 
    if len(g.touches) == 0:
      g.state = GestureData.ENDED
      g.end_time = time.time()
      g.duration = g.end_time - g.start_time
      if not g.moving:
        if g.duration < g.tap_threshold and hasattr(self, 'on_tap'):
          self.on_tap(g)
        elif g.duration > g.long_press_threshold and hasattr(self, 'on_long_press'):
          self.on_long_press(g)
      else:
        if g.swipe_direction and g.duration < GestureData.tap_threshold:
          self.on_swipe(g)
    if hasattr(self, 'on_debug'):
      self.on_debug(g)
          
class GestureView(ui.View, GestureMixin):
  
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.multitouch_enabled = True
  
if __name__ == '__main__':
  
  import copy
  
  class TestView(GestureView):
    
    def __init__(self, **kwargs):
      self.background_color = 'green'
      super().__init__(**kwargs)
      self.status = ui.Label(
        frame=self.bounds, flex='WH', 
        alignment=ui.ALIGN_CENTER, 
        number_of_lines=0,
        text_color='white')
      self.add_subview(self.status)
      self.data = None
      
    def show_status(self, data, gesture_name, data_string=None):
      if data_string is None:
        data_string = f'Loc: {data.location}, Touches: {data.no_of_touches}'
      self.status.text = f'{gesture_name}\n{data_string}'

    def on_tap(self, data):
      self.show_status(data, 'Tap')
      
    def on_long_press(self, data):
      self.show_status(data, 'Long press')
      
    def on_swipe(self, data):
      self.show_status(data, 'Swipe', '')
      
    def on_pan(self, data):
      self.show_status(data, 'Pan')
      
    def on_pinch(self, data):
      self.show_status(data, 'Zoom', f'Scale: {data.scale}')
    
    def on_debug(self, data):
      self.data = copy.deepcopy(data)
      self.set_needs_display()
      
    def draw(self):
      if self.data is None or len(self.data.touches) == 0:
        return 
      for touch in self.data.touches.values():
        (x, y) = touch.location
        p = ui.Path.oval(x-40,y-40,80,80)
        ui.set_color('white')
        p.stroke()
        ui.set_color((0,1,0,0.5))
        p.fill()
      (x, y) = self.data.location
      p = ui.Path()
      p.move_to(x-40, y)
      p.line_to(x+40, y)
      p.move_to(x, y-40)
      p.line_to(x, y+40)
      ui.set_color('darkgreen')
      p.stroke()
      
  v = TestView()
  v.present()
  '''
  t = TapView(
    frame=(0,0, v.width/2, v.height/2), flex='WH')
  v.add_subview(t)
  
  d = DebugView(
    frame=(v.width/2, 0, v.width/2, v.height/2), flex='WH')
  v.add_subview(d)
  '''

