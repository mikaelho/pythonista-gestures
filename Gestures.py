# coding: utf-8

'''
# Gestures for Pythonista
 
This is a convenience class for enabling gestures in Pythonista UI applications, including built-in views. Main intent here has been to make them Python friendly, hiding all the Objective-C stuff. All gestures correspond to the standard Apple gestures, except for the custom force press gesture.

Run the file on its own to see a demo of the supported gestures.

![Demo image](https://raw.githubusercontent.com/mikaelho/pythonista-gestures/master/gestures.jpg)

Get it from [GitHub](https://github.com/mikaelho/pythonista-gestures).

## Example

For example, do something when user swipes left on a TextView:
 
    def swipe_handler(data):
        print(‘I was swiped, starting from ‘ + str(data.location))
     
    tv = ui.TextView()
    Gestures().add_swipe(tv, swipe_handler, direction = Gestures.LEFT)

Your handler method gets one `data` argument that always contains the attributes described below. Individual gestures may provide more information; see the API documentation for the `add_` methods.
  
* `recognizer` - (ObjC) recognizer object
* `view` - (Pythonista) view that captured the object
* `location` - Location of the gesture as a `ui.Point` with `x` and `y` attributes
* `state` - State of gesture recognition; one of `Gestures.POSSIBLE/BEGAN/RECOGNIZED/CHANGED/ENDED/CANCELLED/FAILED`
* `number_of_touches` - Number of touches recognized

For continuous gestures, check for `data.state == Gestures.ENDED` in the handler if you are just interested that a pinch or a force press happened.

All of the `add_x` methods return a `recognizer` object that can be used to remove or disable the gesture as needed, see the API. You can also remove all gestures from a view with `remove_all_gestures(view)`.

#docgen-toc

## Fine-tuning gesture recognition

By default only one gesture recognizer will be successful, but if you want to, for example, enable both zooming (pinch) and panning at the same time, allow both recognizers:

    g = Gestures()
    
    g.recognize_simultaneously = lambda gr, other_gr: gr == Gestures.PAN and other_gr == Gestures.PINCH
    
The other methods you can override are `fail` and `fail_other`, corresponding to the other [UIGestureRecognizerDelegate](https://developer.apple.com/reference/uikit/uigesturerecognizerdelegate?language=objc) methods.
    
All regular recognizers have convenience names that you can use like in the example above: `Gestures.TAP/PINCH/ROTATION/SWIPE/PAN/SCREEN_EDGE_PAN/LONG_PRESS`.

If you need to set these per gesture, instantiate separate `Gestures` objects.

## Pythonista app-closing gesture

When you use the `hide_title_bar=True` attribute with `present`, you close the app with the 2-finger-swipe-down gesture. If your use case requires it, Gestures supports disabling this gesture with:
  
    Gestures.disable_swipe_to_close(view)
    
where the `view` is the one you `present`.

You can also replace the close gesture with another, by providing the "magic" `Gestures.close_app` method as the gesture handler. For example, if you feel that tapping with two thumbs is more convenient in two-handed phone use:
  
    Gestures().add_tap(view, Gestures.close_app, number_of_touches_required=2)

## Notes
 
* Adding a gesture to a view automatically sets `touch_enabled=True` for that view, to avoid counter-intuitive situations where adding a gesture recognizer to e.g. ui.Label produces no results.
* It can be hard to add gestures to ui.ScrollView, ui.TextView and the like, because they have complex multi-view structures and gestures already in place.
* To facilitate the gesture handler callbacks from Objective-C to Python, the Gestures instance used to create the gesture must be live. You do not need to manage that as objc_util.retain_global is used to keep a global reference around. If you for some reason must track the reference manually, you can turn this behavior off with a `retain_global_reference=False` parameter for the constructor.
* Single Gestures instance can be used to add any number of gestures to any number of views, but you can just as well create a new instance whenever and wherever you need to add a new handler.
* If you need to create millions of dynamic gestures in a long-running app, it can be worthwhile to explicitly `remove` them when no longer needed, to avoid a memory leak.
'''

import ui
from objc_util import *

import uuid, weakref
from functools import partial

# https://developer.apple.com/library/prerelease/ios/documentation/UIKit/Reference/UIGestureRecognizer_Class/index.html#//apple_ref/occ/cl/UIGestureRecognizer


class Gestures():

  TYPE_REGULAR = 0
  TYPE_FORCE = 1
  TYPE_STYLUS = 4
  TYPE_ANY = 8

  TAP = b'UITapGestureRecognizer'
  PINCH = b'UIPinchGestureRecognizer'
  ROTATION = b'UIRotationGestureRecognizer'
  SWIPE = b'UISwipeGestureRecognizer'
  PAN = b'UIPanGestureRecognizer'
  SCREEN_EDGE_PAN = b'UIScreenEdgePanGestureRecognizer'
  LONG_PRESS = b'UILongPressGestureRecognizer'

  POSSIBLE = 0
  BEGAN = 1
  RECOGNIZED = 1
  CHANGED = 2
  ENDED = 3
  CANCELLED = 4
  FAILED = 5

  RIGHT = 1
  LEFT = 2
  UP = 4
  DOWN = 8

  EDGE_NONE = 0
  EDGE_TOP = 1
  EDGE_LEFT = 2
  EDGE_BOTTOM = 4
  EDGE_RIGHT = 8
  EDGE_ALL = 15

  def __init__(self, touch_type=TYPE_REGULAR, force_threshold=0.4, retain_global_reference = True):
    self.buttons = {}
    self.views = {}
    self.recognizers = {}
    self.actions = {}
    self.touches = {}
    self.touch_type = touch_type
    self.force_threshold = force_threshold
    if retain_global_reference:
      retain_global(self)

    # Friendly delegate function defaults
    def recognize_simultaneously_default(gr_name, other_gr_name):
      return False
      
    def fail_default(gr_name, other_gr_name):
      return False
      
    def fail_other_default(gr_name, other_gr_name):
      return False    
    
    self.recognize_simultaneously = recognize_simultaneously_default
    self.fail = fail_default
    self.fail_other = fail_other_default

    # ObjC delegate functions
    
    def simplify(func, gr, other_gr):
      gr_o = ObjCInstance(gr)
      other_gr_o = ObjCInstance(other_gr)
      if (gr_o.view() != other_gr_o.view()):
        return False
      gr_name = gr_o._get_objc_classname()
      other_gr_name = other_gr_o._get_objc_classname()
      return func(gr_name, other_gr_name)
    
    # Recognize simultaneously

    def gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer_(_self, _sel, gr, other_gr):
      delegate_instance = ObjCInstance(_self)
      slf = delegate_instance._gestures()
      return simplify(slf.recognize_simultaneously, gr, other_gr)
    
    # Fail other
    
    def gestureRecognizer_shouldRequireFailureOfGestureRecognizer_(_self, _sel, gr, other_gr):
      delegate_instance = ObjCInstance(_self)
      slf = delegate_instance._gestures()
      return simplify(slf.fail_other, gr, other_gr)
    
    # Fail
    
    def gestureRecognizer_shouldBeRequiredToFailByGestureRecognizer_(_self, _sel, gr, other_gr):
      #slf = Gestures.get_self(_self)
      delegate_instance = ObjCInstance(_self)
      slf = delegate_instance._gestures()
      return simplify(slf.fail, gr, other_gr)
    
    # Delegate
    
    try:
      PythonistaGestureDelegate = ObjCClass('PythonistaGestureDelegate')
    except:
      PythonistaGestureDelegate = create_objc_class('PythonistaGestureDelegate',
      superclass=NSObject,
      methods=[
        #gestureRecognizer_shouldReceiveTouch_,
        gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer_,
        gestureRecognizer_shouldRequireFailureOfGestureRecognizer_,
        gestureRecognizer_shouldBeRequiredToFailByGestureRecognizer_],
      classmethods=[],
      protocols=['UIGestureRecognizerDelegate'],
      debug=True)
    self._delegate = PythonistaGestureDelegate.new()
    self._delegate._gestures = weakref.ref(self)

  @on_main_thread
  def add_tap(self, view, action, number_of_taps_required = None, number_of_touches_required = None):
    ''' Call `action` when a tap gesture is recognized for the `view`.
    
    Additional parameters:
      
    * `number_of_taps_required` - Set if more than one tap is required for the gesture to be recognized.
    * `number_of_touches_required` - Set if more than one finger is required for the gesture to be recognized.
    '''
    recog = self._get_recog('UITapGestureRecognizer', view, self._general_action, action)

    if number_of_taps_required:
      recog.numberOfTapsRequired = number_of_taps_required
    if number_of_touches_required:
      recog.numberOfTouchesRequired = number_of_touches_required

    return recog
    
  @on_main_thread
  def add_doubletap(self, view, action, number_of_touches_required = None):
    ''' Convenience method that calls `add_tap` with a 2-tap requirement. '''
    self.add_tap(view, action, number_of_taps_required = 2, number_of_touches_required=number_of_touches_required)

  @on_main_thread
  def add_long_press(self, view, action, number_of_taps_required = None, number_of_touches_required = None, minimum_press_duration = None, allowable_movement = None):
    ''' Call `action` when a long press gesture is recognized for the `view`. Note that this is a continuous gesture; you might want to check for `data.state == Gestures.CHANGED` or `ENDED` to get the desired results.
    
    Additional parameters:
      
    * `number_of_taps_required` - Set if more than one tap is required for the gesture to be recognized.
    * `number_of_touches_required` - Set if more than one finger is required for the gesture to be recognized.
    * `minimum_press_duration` - Set to change the default 0.5 second recognition treshold.
    * `allowable_movement` - Set to change the default 10 point maximum distance allowed for the gesture to be recognized.
    '''
    recog = self._get_recog('UILongPressGestureRecognizer', view, self._general_action, action)

    if number_of_taps_required:
      recog.numberOfTapsRequired = number_of_taps_required
    if number_of_touches_required:
      recog.numberOfTouchesRequired = number_of_touches_required
    if minimum_press_duration:
      recog.minimumPressDuration = minimum_press_duration
    if allowable_movement:
      recog.allowableMovement = allowable_movement

    return recog

  @on_main_thread
  def add_pan(self, view, action, minimum_number_of_touches = None, maximum_number_of_touches = None):
    ''' Call `action` when a pan gesture is recognized for the `view`. This is a continuous gesture.
    
    Additional parameters:
      
    * `minimum_number_of_touches` - Set to control the gesture recognition.
    * `maximum_number_of_touches` - Set to control the gesture recognition.
    
    Handler `action` receives the following gesture-specific attributes in the `data` argument:
      
    * `translation` - Translation from the starting point of the gesture as a `ui.Point` with `x` and `y` attributes.
    * `velocity` - Current velocity of the pan gesture as points per second (a `ui.Point` with `x` and `y` attributes).
    '''
    recog = self._get_recog('UIPanGestureRecognizer', view, self._pan_action, action)

    if minimum_number_of_touches:
      recog.minimumNumberOfTouches = minimum_number_of_touches
    if maximum_number_of_touches:
      recog.maximumNumberOfTouches = maximum_number_of_touches

    return recog

  @on_main_thread
  def add_screen_edge_pan(self, view, action, edges):
    ''' Call `action` when a pan gesture starting from the edge is recognized for the `view`. This is a continuous gesture.
    
    `edges` must be set to one of `Gestures.EDGE_NONE/EDGE_TOP/EDGE_LEFT/EDGE_BOTTOM/EDGE_RIGHT/EDGE_ALL`. If you want to recognize pans from different edges, you have to set up separate recognizers with separate calls to this method.
    
    Handler `action` receives the same gesture-specific attributes in the `data` argument as pan gestures, see `add_pan`.
    '''
    recog = self._get_recog('UIScreenEdgePanGestureRecognizer', view, self._pan_action, action)

    recog.edges = edges

    return recog

  @on_main_thread
  def add_pinch(self, view, action):
    ''' Call `action` when a pinch gesture is recognized for the `view`. This is a continuous gesture.
    
    Handler `action` receives the following gesture-specific attributes in the `data` argument:
    
    * `scale` - Relative to the distance of the fingers as opposed to when the touch first started.
    * `velocity` - Current velocity of the pinch gesture as scale per second.
    '''
    recog = self._get_recog('UIPinchGestureRecognizer', view, self._pinch_action, action)

    return recog

  @on_main_thread
  def add_rotation(self, view, action):
    ''' Call `action` when a rotation gesture is recognized for the `view`. This is a continuous gesture.
    
    Handler `action` receives the following gesture-specific attributes in the `data` argument:
    
    * `rotation` - Rotation in radians, relative to the position of the fingers when the touch first started.
    * `velocity` - Current velocity of the rotation gesture as radians per second.
    '''
    recog = self._get_recog('UIRotationGestureRecognizer', view, self._rotation_action, action)

    return recog

  @on_main_thread
  def add_swipe(self, view, action, direction = None, number_of_touches_required = None):
    ''' Call `action` when a swipe gesture is recognized for the `view`.
    
    Additional parameters:
      
    * `direction` - Direction of the swipe to be recognized. Either one of `Gestures.RIGHT/LEFT/UP/DOWN`, or a list of multiple directions.
    * `number_of_touches_required` - Set if you need to change the minimum number of touches required.
    
    If swipes to multiple directions are to be recognized, the handler does not receive any indication of the direction of the swipe. Add multiple recognizers if you need to differentiate between the directions. 
    '''
    recog = self._get_recog('UISwipeGestureRecognizer', view, self._general_action, action)

    if direction:
      combined_dir = direction
      if isinstance(direction, list):
        combined_dir = 0
        for one_direction in direction:
          combined_dir |= one_direction
      recog.direction = combined_dir
    if number_of_touches_required:
      recog.numberOfTouchesRequired = number_of_touches_required

    return recog
    
  @on_main_thread
  def add_force_press(self, view, action, threshold=0.4):
    ''' Call `action` when a force press gesture is recognized for the `view`. This is a continuous gesture.
    
    Additional parameters:
      
    * `threshold` - How much pressure is required for the gesture to be detected, between 0 and 1. Default is 0.4.
    
    Handler `action` receives the following gesture-specific attributes in the `data` argument:
    
    * `force` - Force of the press, a value between `threshold` and 1.
    '''
    recog = self._get_recog('UILongPressGestureRecognizer', view, partial(self._force_press_action, threshold), action)

    return recog

  @on_main_thread
  def disable(self, recognizer):
    ''' Disable a recognizer temporarily. '''
    ObjCInstance(recognizer).enabled = False

  @on_main_thread
  def enable(self, recognizer):
    ''' Enable a disabled gesture recognizer. There is no error if the recognizer is already enabled. '''
    ObjCInstance(recognizer).enabled = True

  @on_main_thread
  def remove(self, view, recognizer):
    ''' Remove the recognizer from the view permanently. '''
    key = None
    for id in self.recognizers:
      if self.recognizers[id] == recognizer:
        key = id
        break
    if key:
      del self.buttons[key]
      del self.views[key]
      del self.recognizers[key]
      del self.actions[key]
    ObjCInstance(view).removeGestureRecognizer_(recognizer)

  @on_main_thread
  def remove_all_gestures(self, view):
    ''' Remove all gesture recognizers from a view. '''
    gestures = ObjCInstance(view).gestureRecognizers()
    for recog in gestures:
      self.remove(view, recog)
      
  @classmethod
  def disable_swipe_to_close(cls, view):
    ''' Utility class method that will
    disable the two-finger-swipe-down gesture
    used in Pythonista to end the program
    when in full screen view 
    (`hide_title_bar` set to `True`).
    '''
    UILayoutContainerView = ObjCClass('UILayoutContainerView')
    UISwipeGestureRecognizer = ObjCClass('UISwipeGestureRecognizer')
    v = view.objc_instance
    while not v.isKindOfClass_(UILayoutContainerView.ptr):
      v = v.superview()
    for gr in v.gestureRecognizers():
      if gr.isKindOfClass_(UISwipeGestureRecognizer.ptr):
        gr.setEnabled(False)
        return v, gr.valueForKey_('targets')[0].target()
     
  @classmethod
  def replace_close_gesture(cls, view, recog_name):
    recog_name_str = recog_name.decode("utf-8")
    view, target = cls.disable_swipe_to_close(view)
    recognizer = ObjCClass(recog_name).alloc().initWithTarget_action_(target, sel('dismiss:')).autorelease()
    view.addGestureRecognizer_(recognizer)

  def _get_recog(self, recog_name, view, internal_action, final_handler):
    if not final_handler == Gestures.close_app:
      view.touch_enabled = True
      button = ui.Button()
      key = str(uuid.uuid4())
      button.name = key
      button.action = internal_action
      self.buttons[key] = button
      self.views[key] = view
      recognizer = ObjCClass(recog_name).alloc().initWithTarget_action_(button, sel('invokeAction:')).autorelease()
      self.recognizers[key] = recognizer
      self.actions[key] = final_handler
      ObjCInstance(view).addGestureRecognizer_(recognizer)
      recognizer.delegate = self._delegate
      return recognizer
    else:
      view, target = Gestures.disable_swipe_to_close(view)
      recognizer = ObjCClass(recog_name).alloc().initWithTarget_action_(target, sel('dismiss:')).autorelease()
      view.addGestureRecognizer_(recognizer)
      return recognizer

  class Data():
    def __init__(self):
      self.recognizer = self.view = self.location = self.state = self.number_of_touches = self.scale = self.rotation = self.velocity = None

  def _context(self, button):
    key = button.name
    (view, recog, action) = (self.views[key], self.recognizers[key], self.actions[key])
    data = Gestures.Data()
    data.recognizer = recog
    data.view = view
    data.location = self._location(view, recog)
    data.state = recog.state()
    data.number_of_touches = recog.numberOfTouches()
    #data.additional_touch_data = self.touches[recog]
    return (data, action)

  def _location(self, view, recog):
    loc = recog.locationInView_(ObjCInstance(view))
    return ui.Point(loc.x, loc.y)

  def _general_action(self, sender):
    (data, action) = self._context(sender)
    action(data)

  def _pan_action(self, sender):
    (data, action) = self._context(sender)
    trans = data.recognizer.translationInView_(ObjCInstance(data.view))
    vel = data.recognizer.velocityInView_(ObjCInstance(data.view))
    data.translation = ui.Point(trans.x, trans.y)
    data.velocity = ui.Point(vel.x, vel.y)

    action(data)

  def _pinch_action(self, sender):
    (data, action) = self._context(sender)
    data.scale = data.recognizer.scale()
    data.velocity = data.recognizer.velocity()

    action(data)

  def _rotation_action(self, sender):
    (data, action) = self._context(sender)
    data.rotation = data.recognizer.rotation()
    data.velocity = data.recognizer.velocity()

    action(data)
    
  def _force_press_action(self, threshold, sender):
    (data, action) = self._context(sender)
    
    touch = data.recognizer.touches()[0]
    force_fraction = touch.force()/touch.maximumPossibleForce()
    if force_fraction > threshold:
      data.force = force_fraction
      action(data)

  @classmethod
  def close_app(cls):
    pass

    
# TESTING AND DEMONSTRATION

if __name__ == "__main__":
  
  import math, random, console
  
  g = Gestures()
  g2 = Gestures()
    
  bg = ui.View(background_color='black')
  bg.present(hide_title_bar=True)
  g.add_tap(bg, Gestures.close_app, number_of_touches_required=2)
  
  console.hud_alert('Tap with 2 fingers to close the app')
  
  def random_background(view):
    colors = ['#0b6623', '#9dc183', '#3f704d', '#8F9779', '#4F7942', '#A9BA9D', '#D0F0C0', '#043927', '#679267', '#2E8B57']
    view.background_color = random.choice(colors)
    view.text_color = 'black' if sum(view.background_color[:3]) > 1.5 else 'white'

  def update_text(l, text):
    l.text = '\n'.join([l.text.splitlines()[0]] + [text])

  def generic_handler(data):
    update_text(data.view, 'State: ' + str(data.state) + ' Touches: ' + str(data.number_of_touches))
    random_background(data.view)
    
  def long_press_handler(data):
    random_background(data.view)
    if data.state == Gestures.CHANGED:
      update_text(data.view, 'Ongoing')
    elif data.state == Gestures.ENDED:
      update_text(data.view, 'Finished')
    
  def pan_handler(data):
    update_text(data.view, 'Trans: ' + str(data.translation))
    random_background(data.view)
    
  def pinch_handler(data):
    random_background(data.view)
    update_text(data.view, 'Scale: ' + str(round(data.scale, 6)))
    
  def pan_or_pinch_handler(data):
    random_background(data.view)
    if hasattr(data, 'translation'):
      update_text(data.view, 'Pan')
    elif hasattr(data, 'scale'):
      update_text(data.view, 'Pinch')
    else:
      update_text(data.view, 'Something else')
      
  def pan_or_swipe_handler(data):
    random_background(data.view)
    if hasattr(data, 'translation'):
      update_text(data.view, 'Pan')
    else:
      update_text(data.view, 'Swipe')
      
  def force_handler(data):
    base_color = (.82, .94, .75)
    color_actual = [c*data.force for c in base_color]
    data.view.background_color = tuple(color_actual)
    data.view.text_color = 'black' if sum(color_actual) > 1.5 else 'white'
    update_text(data.view, 'Force: ' + str(round(data.force, 6)))
    
  def stylus_handler(data):
    random_background(data.view)
  
  edge_l = ui.Label(
    text='Edge pan (from right)', 
    background_color='grey',
    text_color='white',
    alignment=ui.ALIGN_CENTER,
    number_of_lines=0,
    frame=(
      0, 0, bg.width, 75
  ))
  bg.add_subview(edge_l)
  g.add_screen_edge_pan(edge_l, pan_handler, edges=Gestures.EDGE_RIGHT)

  v = ui.ScrollView(frame=(0, 75, bg.width, bg.height-75))
  bg.add_subview(v)
  
  label_count = -1
  
  def create_label(title):
    global label_count
    label_count += 1
    label_w = 175
    label_h = 75
    gap = 5
    label_w_with_gap = label_w + gap
    label_h_with_gap = label_h + gap
    labels_per_line = math.floor((v.width-2*gap)/(label_w+gap))
    left_margin = (v.width - labels_per_line*label_w_with_gap + gap)/2
    line = math.floor(label_count/labels_per_line)
    column = label_count - line*labels_per_line
    
    l = ui.Label(
      text=title, 
      background_color='grey',
      text_color='white',
      alignment=ui.ALIGN_CENTER,
      number_of_lines=0,
      frame=(
        left_margin+column * label_w_with_gap,
        gap+line * label_h_with_gap,
        label_w, label_h
    ))
    v.add_subview(l)
    return l

  tap_l = create_label('Tap')
  g.add_tap(tap_l, generic_handler)
  
  tap_2_l = create_label('Doubletap')
  g.add_doubletap(tap_2_l, generic_handler)
    
  long_l = create_label('Long press')
  g.add_long_press(long_l, long_press_handler)
  
  pan_l = create_label('Pan')
  g.add_pan(pan_l, pan_handler)
  
  swipe_l = create_label('Swipe (right)')
  g.add_swipe(swipe_l, generic_handler, direction=Gestures.RIGHT)
  
  pinch_l = create_label('Pinch')
  g.add_pinch(pinch_l, pinch_handler)
  
  pan_or_pinch_l = create_label('Pan or pinch')
  g.add_pan(pan_or_pinch_l, pan_or_pinch_handler)
  g.add_pinch(pan_or_pinch_l, pan_or_pinch_handler)
  
  g.fail_other = lambda gr, other_gr: gr == Gestures.PAN and other_gr == Gestures.SWIPE
  
  pan_or_swipe_l = create_label('Pan or swipe (right)')
  g.add_pan(pan_or_swipe_l, pan_or_swipe_handler)
  g.add_swipe(pan_or_swipe_l, pan_or_swipe_handler, direction=Gestures.RIGHT)
  
  force_l = create_label('Force press')
  g2.add_force_press(force_l, force_handler)

