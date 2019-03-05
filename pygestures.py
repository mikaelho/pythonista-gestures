'''
Mixin class to be inherited together with Pythonista ui.View for gesture support.

Implement following methods to handle gestures:
* on_tap
* on_pinch
* on_pan
'''

import time, math
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

  gestures = (
    'tap', 'long_press',
    'swipe', 'swipe_up', 'swipe_left', 'swipe_right', 'swipe_down',
    'pan', 'pinch', 'rotate'
  )
  
  tap_threshold = 0.3 # seconds
  long_press_threshold = 0.5 # second
  move_threshold = 15 # pixels
  
  NOT_POSSIBLE = None
  CANCELLED = -2
  ENDED = -1
  POSSIBLE = 0
  BEGAN = 1
  CHANGED = 2
  FAILED = 3

  UP = 'up'
  DOWN = 'down'
  LEFT = 'left'
  RIGHT = 'right'
  
  def __init__(self, view):
    self.view = view
    
    self.gesture_states = {}
    self.reset(*self.gestures)
      
    self.touches = {}
    self.touches_in_order = []
    self.no_of_touches = 0   
    self.state = None

    self.location = None
    self.prev_location = None
    
  def reset(self, *gestures):
    for gesture in gestures:
      self.gesture_states[gesture] = (self.POSSIBLE
        if hasattr(self.view, 'on_'+gesture) else
        self.NOT_POSSIBLE)
      if gesture == 'pan':
        self.start_translation = None
        self.translation = None
        self.prev_translation = None
      if gesture == 'pinch':
        self.start_pinch_distance = None
        self.pinch_distance = None
        self.prev_pinch_distance = None
        self.scale = None
      if gesture == 'rotate':
        self.start_angle = None
        self.angle = None
        self.prev_angle = None
        self.rotation = None
    
  def is_possible(self, *gestures):
    return all((self.gesture_states[gesture] == self.POSSIBLE for gesture in gestures))
    
  def is_active(self, *gestures):
    return all((self.gesture_states[gesture] in (self.POSSIBLE, self.BEGAN, self.CHANGED) for gesture in gestures))
    
  def has_begun(self, gesture):
    return self.gesture_states[gesture] == self.BEGAN
    
  def fail(self, *gestures):
    for gesture in gestures:
      self.gesture_states[gesture] = self.FAILED
      
  def none_possible(self, *gestures):
    return not any((
      self.gesture_states[gesture] == self.POSSIBLE for gesture in gestures))
    
  def check(self, *gestures):
    for gesture in gestures:
      if self.is_active(gesture):
        if self.is_possible(gesture):
          self.began(gesture)
        else:
          self.changed(gesture)
    
  def began(self, gesture):
    self.gesture_states[gesture] = self.BEGAN
    self.state = self.BEGAN
    getattr(self.view, 'on_'+gesture)(self)
    
  def changed(self, gesture):
    self.gesture_states[gesture] = self.CHANGED
    self.state = self.CHANGED
    getattr(self.view, 'on_'+gesture)(self)
    
  def end(self, gesture):
    self.gesture_states[gesture] = self.ENDED
    self.state = self.ENDED
    getattr(self.view, 'on_'+gesture)(self)
    
  def soft_end(self, gesture):
    self.end(gesture)
    self.reset(gesture)
    
  @property
  def out_of_business(self):
    return any((state is not None and state < self.POSSIBLE for state in self.gesture_states.values()))
    
  def get_center_location(self):
    center_loc = Point(0,0)
    for touch in self.touches.values():
      center_loc += Point(*touch.location)
    center_loc /= len(self.touches)     
    return center_loc
    
  def get_pinch_distance(self):
    distance_vector = (
      self.touches_in_order[0].location -  
      self.touches_in_order[1].location)
    return abs(distance_vector)
    
  def get_angle(self):
    if self.first_touch and self.second_touch:
      return self.degrees(
        self.second_touch.location - 
        self.first_touch.location)
    else:
      return 0
    
  def radians(self, vector):
    rad = math.atan2(vector.y, vector.x)
    return rad
    
  def degrees(self, vector):
    return math.degrees(self.radians(vector))
    
    '''
    center = self.center_location()
    sum_degrees = 0
    for touch in self.touches.values():
      sum_degrees += self.degrees(touch.location - center)
    return sum_degrees/len(self.touches)
    '''
    

class GestureMixin():
  
  def touch_began(self, touch):
    
    if not hasattr(self, '_gestures') or len(self._gestures.touches) == 0:
      self._gestures = GestureData(self)
    g = self._gestures
    
    if g.out_of_business:
      return

    if len(g.touches) == 0:
      g.start_time = time.time()
      
    t = GestureTouch(touch.location)
    g.touches[touch.touch_id] = t
    g.touches_in_order.append(t)
    
    g.no_of_touches = max(g.no_of_touches, len(g.touches))
    
    g.prev_location = g.location
    g.location = g.get_center_location()
    
    if g.start_translation is None:
      g.start_translation = touch.location
    else:
      g.start_translation += g.location - g.prev_location
    
    if len(g.touches) >= 2:
      g.prev_pinch_distance = g.pinch_distance
      g.pinch_distance = g.get_pinch_distance()
      
      if g.start_pinch_distance is None:
        g.start_pinch_distance = g.pinch_distance
      else:
        g.start_pinch_distance += g.pinch_distance - g.prev_pinch_distance

        
      #g.start_angle = g.angle
    
    '''
      

    
      
    if g.first_touch and g.second_touch:
      g.prev_angle = g.angle
      g.angle = g.get_angle()
      if g.start_angle is None:
        g.start_angle = g.angle
      #else:
      #  g.start_angle += g.angle - g.prev_angle
    '''
    
  def touch_moved(self, touch):
    g = self._gestures
    if g.out_of_business:
      return
      
    t = g.touches[touch.touch_id]
    g.duration = time.time() - g.start_time
    t.location = touch.location
    g.prev_location = g.location
    g.location = g.get_center_location()
    g.translation = g.location - g.start_translation
    
    if t.distance_from_start > g.move_threshold:
      g.fail('tap', 'long_press')
      
    if g.duration > g.tap_threshold:
      g.fail('tap', 'swipe', 'swipe_left', 'swipe_right', 'swipe_up', 'swipe_down')
      
    if g.is_possible('long_press') and g.duration > g.long_press_threshold:
      g.end('long_press')
      return
      
    if g.none_possible('tap', 'long_press', 
      'swipe', 'swipe_left', 'swipe_right', 
      'swipe_up', 'swipe_down'):
      g.check('pan')
      if len(g.touches) >= 2:      
        g.prev_pinch_distance = g.pinch_distance
        g.pinch_distance = g.get_pinch_distance()
        g.scale = g.pinch_distance/g.start_pinch_distance
        g.check('pinch')
    
    '''
    g.prev_angle = g.angle
    g.angle = g.get_angle()

    '''
    '''
    if not g.moving:
      if t.distance_from_start > g.move_threshold:
        g.moving = True
    if (not g.moving and
      g.duration > g.long_press_threshold and 
      hasattr(self, 'on_long_press')):
      self.on_long_press(g)
      g.state = GestureData.COMPLETE

    if g.moving:
      if (self.swiping_enabled and
        g.duration < GestureData.tap_threshold):
        g.swipe_direction = True
      else:
        g.swipe_direction = None
        if hasattr(self, 'on_pan'):
          if not g.panning:
            g.panning = True
            g.state = g.BEGAN
          else:
            g.state = g.MOVED
          self.on_pan(g)
        if g.first_touch and g.second_touch:
          g.scale = g.pinch_distance/g.start_pinch_distance
          g.rotation = g.angle - g.start_angle
          if len(g.touches) == 2 and hasattr(self, 'on_pinch'):
            if not g.pinching:
              g.pinching = True
              g.state = g.BEGAN
            else:
              g.state = g.MOVED
            self.on_pinch(g)
          if hasattr(self, 'on_rotate'):
            if not g.rotating:
              g.rotating = True
              g.state = g.BEGAN
            else:
              g.state = g.MOVED
            self.on_rotate(g)
      g.state = GestureData.MOVED
    '''
    #if hasattr(self, 'on_debug'):
    #  self.on_debug(g)
    
  def touch_ended(self, touch):
    g = self._gestures
    '''
    t = g.touches[touch.touch_id]
    if t == g.first_touch or t == g.second_touch:
      g.first_touch = None
      g.second_touch = None
    '''
    del g.touches[touch.touch_id]
    if g.out_of_business:
      return
      
    if len(g.touches) > 0:
      g.prev_location = g.location
      g.location = g.get_center_location()
      if g.is_active('pan'):
        g.start_translation += g.location - g.prev_location
      
      g.prev_pinch_distance = g.pinch_distance
      g.pinch_distance = g.get_pinch_distance()
      if g.is_active('pinch'):
        if len(g.touches) > 1:
          g.start_pinch_distance += g.pinch_distance - g.prev_pinch_distance
        else:
          g.soft_end('pinch')
        
      '''
      if g.first_touch and g.second_touch:
        g.prev_angle = g.angle
        g.angle = g.get_angle()
        if g.rotating:
          g.start_angle += g.angle - g.prev_angle
      '''
        
    if len(g.touches) == 0:
      g.end_time = time.time()
      g.duration = g.end_time - g.start_time

      if g.is_possible('tap'):
        g.end('tap')
        return
        
      delta = g.translation
      if abs(delta.x) > abs(delta.y):
        g.swipe_direction = g.RIGHT if delta.x > 0 else g.LEFT
      else:
        g.swipe_direction = g.DOWN if delta.y > 0 else g.UP
      swiped = False
      gesture = 'swipe_'+g.swipe_direction
      if g.is_possible(gesture):
        g.end(gesture)
        swiped = True
      if g.is_possible('swipe'):
        g.end('swipe')
        swiped = True
      if swiped:
        return 
        
      '''
      else:
        if g.swipe_direction and g.duration < GestureData.tap_threshold:

      '''
    #if hasattr(self, 'on_debug'):
    #  self.on_debug(g)
          
class GestureView(ui.View, GestureMixin):
  
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.multitouch_enabled = True
  
if __name__ == '__main__':
  
  import copy
  
  class TestView(GestureView):
    
    def __init__(self, **kwargs):
      self.background_color = 'black'
      super().__init__(**kwargs)
      self.data = None
      self.labels = {}
      self.translate_track = []
      
    def create_labels(self):
      self.create_label('Tap')
      self.create_label('Long press')
      self.create_label('Swipe')
      self.create_label('Pan')
      self.create_label('Pinch')
      self.create_label('Rotate')
      
    def create_label(self, name):
      l = ui.Label(name=name,
        x=0, flex='TBRW', 
        alignment=ui.ALIGN_CENTER, 
        number_of_lines=0,
        text_color=(1,1,1,0.5))
      l.y = self.height/6 * len(self.subviews)
      l.width = self.width
      self.add_subview(l)
      
    def show_status(self, data, gesture_name, data_string=None):
      l = self[gesture_name]
      if data_string is None:
        data_string = f'Loc: {data.location}, Touches: {data.no_of_touches}'
      l.text = f'{gesture_name}\n{data_string}'
      self.data = data
      self.set_needs_display()

    def on_tap(self, data):
      self.show_status(data, 'Tap')
      
    def on_long_press(self, data):
      self.show_status(data, 'Long press')
      
    def on_swipe(self, data):
      self.show_status(data, 'Swipe', data.swipe_direction)
      
    def on_pan(self, data):
      self.show_status(data, 'Pan', f'Translation: {data.translation}')
      if data.state == data.BEGAN:
        self.translate_track = [data.translation]
      else:
        self.translate_track.append(data.translation)
      self.translate_track = self.translate_track[-20:]
      
    def on_pinch(self, data):
      self.show_status(data, 'Pinch', f'Scale: {data.scale}')
      
    def on_rotate(self, data):
      self.data = copy.deepcopy(data)
      self.show_status(data, 'Rotate', f'Angle: {data.rotation}')
    
    def on_debug(self, data):
      self.data = copy.deepcopy(data)
      self.set_needs_display()
      
    def draw(self):
      if self.data is None or len(self.data.touches) == 0:
        return
      c = self.bounds.center()
      if self.data.translation is not None:
        c += self.data.translation
      for touch in self.data.touches.values():
        (x, y) = touch.location
        p = ui.Path.oval(x-40, y-40, 80, 80)
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
      
      '''
      if len(self.translate_track) > 1:
        p = ui.Path()
        p.move_to(*(self.bounds.center() + self.translate_track[0]))
        for pos in self.translate_track[1:]:
          p.line_to(*(self.bounds.center() + pos))
        ui.set_color((1,0,0,0.5))
        p.stroke()
      '''
        
      if self.data.translation is not None:
        radius = 40 * self.data.scale if self.data.scale is not None else 1
        p = ui.Path.oval(c.x-radius, c.y-radius, 2*radius, 2*radius)
        ui.set_color('red')
        p.stroke()
        if self.data.rotation is not None:
          p = ui.Path()
          p.move_to(c.x, c.y)
          p.line_to(c.x+radius, c.y)
          clockwise = self.data.rotation >= 0
          p.add_arc(c.x, c.y, radius, 0, 
            math.radians(self.data.rotation), 
            clockwise)
          p.line_to(c.x, c.y)
          ui.set_color((1,0,0,0.5))
          p.fill()
          ui.set_color('red')
          p.stroke()
      
  v = TestView()
  v.present(title_bar_color='black')
  v.create_labels()

  '''
  t = TapView(
    frame=(0,0, v.width/2, v.height/2), flex='WH')
  v.add_subview(t)
  
  d = DebugView(
    frame=(v.width/2, 0, v.width/2, v.height/2), flex='WH')
  v.add_subview(d)
  '''

