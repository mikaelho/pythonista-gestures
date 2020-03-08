# coding: utf-8

"""
Gestures wrapper for iOS

# Gestures for the Pythonista iOS app
 
This is a convenience class for enabling gestures in Pythonista UI
applications, including built-in views. Main intent here has been to make
them Python friendly, hiding all the Objective-C stuff. All gestures
correspond to the standard Apple gestures.

Run the file on its own to see a demo of the supported gestures.

![Demo image](https://raw.githubusercontent.com/mikaelho/pythonista-gestures/master/gestures.jpg)

## Installation

Copy from [GitHub](https://github.com/mikaelho/pythonista-gestures), or

    pip install pythonista-gestures

with [stash](https://github.com/ywangd/stash).

## Usage

For example, do something when user swipes left on a Label:
 
    import gestures

    def swipe_handler(data):
        print(f‘I was swiped, starting from {data.location}')
     
    label = ui.Label()
    gestures.swipe(label, swipe_handler, direction=gestures.LEFT)

Your handler method gets one `data` argument that always contains the
attributes described below. Individual gestures may provide more
information; see the API documentation for the methods used to add different
gestures.
  
* `recognizer` - (ObjC) recognizer object
* `view` - (Pythonista) view that was gestured at
* `location` - Location of the gesture as a `ui.Point` with `x` and `y`
  attributes
* `state` - State of gesture recognition; one of
  `gestures.POSSIBLE/BEGAN/RECOGNIZED/CHANGED/ENDED/CANCELLED/FAILED`
* `began`, `changed`, `ended`, `failed` - convenience boolean properties to 
  check for these states
* `number_of_touches` - Number of touches recognized

For continuous gestures, check for `data.began` or `data.ended` in the handler 
if you are just interested that a pinch or a force press happened.

All of the gesture-adding methods return an object that can be used
to remove or disable the gesture as needed, see the API. You can also remove
all gestures from a view with `remove_all_gestures(view)`.

#docgen-toc

## Fine-tuning gesture recognition

By default only one gesture recognizer will be successful. You can prioritize
one over the other by using the `before` method of the returned object.
For example, the following ensures that the swipe always has a chance to happen
first:
    
    panner = pan(view, pan_handler)
    swiper = swipe(view, swipe_handler, direction=RIGHT)
    swiper.before(panner)
    
(For your convenience, there is also a similar `after` method.)

You can also allow gestures to be recognized simultaneously using the
`together_with` method. For example, the following enables simultaneous panning
and zooming (pinching):
    
    panner = pan(view, pan_handler)
    pincher = pinch(view, pinch_handler)
    panner.together_with(pincher)

## Using lambdas

If there in existing method that you just want to trigger with a gesture,
often you do not need to create an extra handler function.
This works best with the discrete `tap` and `swipe` gestures where we do not
need to worry with the state of the gesture.

    tap(label, lambda _: setattr(label, 'text', 'Tapped'))

The example below triggers some kind of a database refresh when a long press is
detected on a button.
Anything more complicated than this is probably worth creating a separate
function.
    
    long_press(button, lambda data: db.refresh() if data.began else None)

## Pythonista app-closing gesture

When you use the `hide_title_bar=True` attribute with `present`, you close
the app with the 2-finger-swipe-down gesture. This gesture can be
disabled with:
  
    gestures.disable_swipe_to_close(view)
    
where the `view` must be the one you `present`.

You can also replace the close gesture with another, by providing the
"magic" `close` string as the gesture handler. For example,
if you feel that tapping with two thumbs is more convenient in two-handed
phone use:
  
    gestures.tap(view, 'close', number_of_touches_required=2)

## Other details
 
* Adding a gesture to a view automatically sets `touch_enabled=True` for that
  view, to avoid counter-intuitive situations where adding a gesture
  recognizer to e.g. ui.Label produces no results.
* It can be hard to add gestures to ui.ScrollView, ui.TextView and the like,
  because they have complex multi-view structures and gestures already in
  place.
  
## Versions:
    
* 1.1 - Adds distance parameters to swipe gestures.
* 1.0 - First version released to PyPi. 
  Breaks backwards compatibility in syntax, adds multi-recognizer coordination,
  and removes force press support.
"""

__version__ = '1.1'

import types

import ui
from objc_util import *

# Recognizer classes

UITapGestureRecognizer = ObjCClass('UITapGestureRecognizer')
UILongPressGestureRecognizer = ObjCClass('UILongPressGestureRecognizer')
UIPanGestureRecognizer = ObjCClass('UIPanGestureRecognizer')
UIScreenEdgePanGestureRecognizer = ObjCClass('UIScreenEdgePanGestureRecognizer')
UIPinchGestureRecognizer = ObjCClass('UIPinchGestureRecognizer')
UIRotationGestureRecognizer = ObjCClass('UIRotationGestureRecognizer')
UISwipeGestureRecognizer = ObjCClass('UISwipeGestureRecognizer')

# Constants

# Recognizer states

POSSIBLE = 0
BEGAN = 1
RECOGNIZED = 1
CHANGED = 2
ENDED = 3
CANCELLED = 4
FAILED = 5

# Swipe directions

RIGHT = 1
LEFT = 2
UP = 4
DOWN = 8

# Edge pan, starting edge

EDGE_NONE = 0
EDGE_TOP = 1
EDGE_LEFT = 2
EDGE_BOTTOM = 4
EDGE_RIGHT = 8
EDGE_ALL = 15

class Data():
    """
    Simple class that contains all the data about the gesture. See the Usage
    section and individual gestures for information on the data included. 
    Also provides convenience state-specific properties (`began` etc.).
    """
    
    def __init__(self):
        self.recognizer = self.view = self.location = self.state = \
            self.number_of_touches = self.scale = self.rotation = \
            self.velocity = None

    def __str__(self):
        str_states = (
            'possible',
            'began',
            'changed',
            'ended',
            'cancelled',
            'failed'
        )
        result = 'Gesture data object:'
        for key in dir(self):
            if key.startswith('__'): continue
            result += '\n'
            if key == 'state':
                value = f'{str_states[self.state]} ({self.state})'
            elif key == 'recognizer':
                value = self.recognizer.stringValue()
            elif key == 'view':
                value = self.view.name or self.view
            else:
                value = getattr(self, key)
            result += f'  {key}: {value}'
        return result

    def __repr__(self):
        return f'{type(self)}: {self.__dict__}'

    @property
    def began(self):
        return self.state == BEGAN

    @property
    def changed(self):
        return self.state == CHANGED

    @property
    def ended(self):
        return self.state == ENDED
        
    @property
    def failed(self):
        return self.state == FAILED
            
def is_objc_type(objc_instance, objc_class):
    return objc_instance.isKindOfClass_(objc_class.ptr)
            
def gestureAction(_self, _cmd):
    slf = ObjCInstance(_self)
    view = slf.view
    recognizer = slf.recognizer
    handler_func = slf.handler_func
    data = Data()
    data.recognizer = recognizer
    data.view = view
    location = recognizer.locationInView_(view.objc_instance)
    data.location = ui.Point(location.x, location.y)
    data.state = recognizer.state()
    data.number_of_touches = recognizer.numberOfTouches()
    
    if (is_objc_type(recognizer, UIPanGestureRecognizer) or 
    is_objc_type(recognizer, UIScreenEdgePanGestureRecognizer)):
        trans = recognizer.translationInView_(ObjCInstance(view))
        vel = recognizer.velocityInView_(ObjCInstance(view))
        data.translation = ui.Point(trans.x, trans.y)
        data.velocity = ui.Point(vel.x, vel.y)
    elif is_objc_type(recognizer, UIPinchGestureRecognizer):
        data.scale = recognizer.scale()
        data.velocity = recognizer.velocity()
    elif is_objc_type(recognizer, UIRotationGestureRecognizer):
        data.rotation = recognizer.rotation()
        data.velocity = recognizer.velocity()

    handler_func(data)
    
def gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer_(
        _self, _sel, _gr, _other_gr):
    slf = ObjCInstance(_self)
    other_gr = ObjCInstance(_other_gr)
    return other_gr in slf.other_recognizers

GestureHandler = create_objc_class(
    'GestureHandler',
    superclass=NSObject,
    methods=[
        gestureAction,
        gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer_
    ],
    protocols=['UIGestureRecognizerDelegate']
)

def _get_handler(recognizer_class, view, handler_func):
    view.touch_enabled = True
    handler = GestureHandler.new().autorelease()
    retain_global(handler)

    if handler_func == 'close':
        recognizer = replace_close_gesture(view, recognizer_class)
    else:
        recognizer = recognizer_class.alloc().initWithTarget_action_(
            handler, 'gestureAction').autorelease()
        view.objc_instance.addGestureRecognizer_(recognizer)

    handler.view = view
    handler.recognizer = recognizer
    handler.handler_func = handler_func
    handler.other_recognizers = []

    @on_main_thread
    def before(self, other):
        other.recognizer.requireGestureRecognizerToFail_(
            self.recognizer)

    @on_main_thread
    def after(self, other):
        self.recognizer.requireGestureRecognizerToFail_(
            other.recognizer)
            
    @on_main_thread
    def together_with(self, other):
        self.other_recognizers.append(other.recognizer)
        self.recognizer.delegate = self
            
    setattr(handler, 'before', types.MethodType(before, handler))
    setattr(handler, 'after', types.MethodType(after, handler))
    setattr(handler, 'together_with', types.MethodType(together_with, handler))

    return handler

@on_main_thread
def tap(view, action, 
        number_of_taps_required=None, number_of_touches_required=None):
    """ Call `action` when a tap gesture is recognized for the `view`.

    Additional parameters:

    * `number_of_taps_required` - Set if more than one tap is required for
      the gesture to be recognized.
    * `number_of_touches_required` - Set if more than one finger is
      required for the gesture to be recognized.
    """
    handler = _get_handler(UITapGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if number_of_taps_required:
        recognizer.numberOfTapsRequired = number_of_taps_required
    if number_of_touches_required:
        recognizer.numberOfTouchesRequired = number_of_touches_required

    return handler


@on_main_thread
def doubletap(view, action, 
        number_of_touches_required=None):
    """ Convenience method that calls `tap` with a 2-tap requirement.
    """
    return tap(view, action,
        number_of_taps_required=2,
        number_of_touches_required=number_of_touches_required)

@on_main_thread
def long_press(view, action,
        number_of_taps_required=None,
        number_of_touches_required=None,
        minimum_press_duration=None,
        allowable_movement=None):
    """ Call `action` when a long press gesture is recognized for the
    `view`. Note that this is a continuous gesture; you might want to
    check for `data.changed` or `data.ended` to get the desired results.

    Additional parameters:

    * `number_of_taps_required` - Set if more than one tap is required for
      the gesture to be recognized.
    * `number_of_touches_required` - Set if more than one finger is
      required for the gesture to be recognized.
    * `minimum_press_duration` - Set to change the default 0.5-second
      recognition treshold.
    * `allowable_movement` - Set to change the default 10 point maximum
    distance allowed for the gesture to be recognized.
    """
    handler = _get_handler(UILongPressGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if number_of_taps_required:
        recognizer.numberOfTapsRequired = number_of_taps_required
    if number_of_touches_required:
        recognizer.numberOfTouchesRequired = number_of_touches_required
    if minimum_press_duration:
        recognizer.minimumPressDuration = minimum_press_duration
    if allowable_movement:
        recognizer.allowableMovement = allowable_movement

    return handler

@on_main_thread
def pan(view, action,
        minimum_number_of_touches=None,
        maximum_number_of_touches=None):
    """ Call `action` when a pan gesture is recognized for the `view`.
    This is a continuous gesture.

    Additional parameters:

    * `minimum_number_of_touches` - Set to control the gesture recognition.
    * `maximum_number_of_touches` - Set to control the gesture recognition.

    Handler `action` receives the following gesture-specific attributes
    in the `data` argument:

    * `translation` - Translation from the starting point of the gesture
      as a `ui.Point` with `x` and `y` attributes.
    * `velocity` - Current velocity of the pan gesture as points per
      second (a `ui.Point` with `x` and `y` attributes).
    """
    handler = _get_handler(UIPanGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if minimum_number_of_touches:
        recognizer.minimumNumberOfTouches = minimum_number_of_touches
    if maximum_number_of_touches:
        recognizer.maximumNumberOfTouches = maximum_number_of_touches

    return handler

@on_main_thread
def edge_pan(view, action, edges):
    """ Call `action` when a pan gesture starting from the edge is
    recognized for the `view`. This is a continuous gesture.

    `edges` must be set to one of
    `gestures.EDGE_NONE/EDGE_TOP/EDGE_LEFT/EDGE_BOTTOM/EDGE_RIGHT
    /EDGE_ALL`. If you want to recognize pans from different edges,
    you have to set up separate recognizers with separate calls to this
    method.

    Handler `action` receives the same gesture-specific attributes in
    the `data` argument as pan gestures, see `pan`.
    """
    handler = _get_handler(UIScreenEdgePanGestureRecognizer, view, action)

    handler.recognizer.edges = edges

    return handler

@on_main_thread
def pinch(view, action):
    """ Call `action` when a pinch gesture is recognized for the `view`.
    This is a continuous gesture.

    Handler `action` receives the following gesture-specific attributes
    in the `data` argument:

    * `scale` - Relative to the distance of the fingers as opposed to when
      the touch first started.
    * `velocity` - Current velocity of the pinch gesture as scale
      per second.
    """
    handler = _get_handler(UIPinchGestureRecognizer, view, action)

    return handler

@on_main_thread
def rotation(view, action):
    """ Call `action` when a rotation gesture is recognized for the `view`.
    This is a continuous gesture.

    Handler `action` receives the following gesture-specific attributes
    in the `data` argument:

    * `rotation` - Rotation in radians, relative to the position of the
      fingers when the touch first started.
    * `velocity` - Current velocity of the rotation gesture as radians
      per second.
    """
    handler = _get_handler(UIRotationGestureRecognizer, view, action)

    return handler

@on_main_thread
def swipe(view, action,
        direction=None,
        number_of_touches_required=None,
        min_distance=None,
        max_distance=None):
    """ Call `action` when a swipe gesture is recognized for the `view`.

    Additional parameters:

    * `direction` - Direction of the swipe to be recognized. Either one of
      `gestures.RIGHT/LEFT/UP/DOWN`, or a list of multiple directions.
    * `number_of_touches_required` - Set if you need to change the minimum
      number of touches required.
    * `min_distance` - Minimum distance the swipe gesture must travel in
      order to be recognized. Default is 50.
      This uses an undocumented recognizer attribute.
    * `max_distance` - Maximum distance the swipe gesture can travel in
      order to still be recognized. Default is a very large number.
      This uses an undocumented recognizer attribute.

    If set to recognize swipes to multiple directions, the handler
    does not receive any indication of the direction of the swipe. Add
    multiple recognizers if you need to differentiate between the
    directions.
    """
    handler = _get_handler(UISwipeGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if direction:
        combined_dir = direction
        if isinstance(direction, list):
            combined_dir = 0
            for one_direction in direction:
                combined_dir |= one_direction
        recognizer.direction = combined_dir
    if number_of_touches_required:
        recognizer.numberOfTouchesRequired = number_of_touches_required
    if min_distance:
        recognizer.minimumPrimaryMovement = min_distance
    if max_distance:
        recognizer.maximumPrimaryMovement = max_distance

    return handler

@on_main_thread
def disable(handler):
    """ Disable a recognizer temporarily. """
    handler.recognizer.enabled = False

@on_main_thread
def enable(handler):
    """ Enable a disabled gesture recognizer. There is no error if the
    recognizer is already enabled. """
    handler.recognizer.enabled = True

@on_main_thread
def remove(view, handler):
    ''' Remove the recognizer from the view permanently. '''
    view.objc_instance.removeGestureRecognizer_(handler.recognizer)

@on_main_thread
def remove_all_gestures(view):
    ''' Remove all gesture recognizers from a view. '''
    gestures = view.objc_instance.gestureRecognizers()
    for recognizer in gestures:
        remove(view, recognizer)

@on_main_thread
def disable_swipe_to_close(view):
    """ Utility class method that will disable the two-finger-swipe-down
    gesture used in Pythonista to end the program when in full screen
    view (`hide_title_bar` set to `True`).

    Returns a tuple of the actual ObjC view and dismiss target.
    """
    UILayoutContainerView = ObjCClass('UILayoutContainerView')
    v = view.objc_instance
    while not v.isKindOfClass_(UILayoutContainerView.ptr):
        v = v.superview()
    for gr in v.gestureRecognizers():
        if gr.isKindOfClass_(UISwipeGestureRecognizer.ptr):
            gr.setEnabled(False)
            return v, gr.valueForKey_('targets')[0].target()

@on_main_thread
def replace_close_gesture(view, recognizer_class):
    view, target = disable_swipe_to_close(view)
    recognizer = recognizer_class.alloc().initWithTarget_action_(
        target, sel('dismiss:')).autorelease()
    view.addGestureRecognizer_(recognizer)
    return recognizer


if __name__ == '__main__':

    import math, random, console

    bg = ui.View(background_color='black')
    bg.present('fullscreen', hide_title_bar=True)

    tap(bg, 'close', number_of_touches_required=2)
    console.hud_alert('Tap with 2 fingers to close the app')

    def random_background(view):
        colors = ['#0b6623', '#9dc183', '#3f704d', '#8F9779', '#4F7942',
                  '#A9BA9D', '#D0F0C0', '#043927', '#679267', '#2E8B57']
        view.background_color = random.choice(colors)
        view.text_color = 'black' if sum(
            view.background_color[:3]) > 1.5 else 'white'

    def update_text(l, text):
        l.text = '\n'.join([l.text.splitlines()[0]] + [text])

    def generic_handler(data):
        update_text(data.view,
            'State: ' + str(data.state) + ' Touches: ' + str(
                data.number_of_touches))
        random_background(data.view)

    def long_press_handler(data):
        random_background(data.view)
        if data.changed:
            update_text(data.view, 'Ongoing')
        elif data.ended:
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
            
    def pan_and_pinch_handler(data):
        if hasattr(data, 'translation'):
            random_background(data.view)
        elif hasattr(data, 'scale'):
            update_text(data.view, 'Scale: ' + str(round(data.scale, 6)))
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
        color_actual = [c * data.force for c in base_color]
        data.view.background_color = tuple(color_actual)
        data.view.text_color = 'black' if sum(color_actual) > 1.5 else 'white'
        update_text(data.view, 'Force: ' + str(round(data.force, 6)))

    edge_l = ui.Label(
        text='Edge pan (from right)',
        background_color='grey',
        text_color='white',
        alignment=ui.ALIGN_CENTER,
        number_of_lines=0,
        frame=(
            0, 0, bg.width, 100
        ))
    bg.add_subview(edge_l)
    edge_pan(edge_l, pan_handler, edges=EDGE_RIGHT)

    v = ui.ScrollView(frame=(0, 100, bg.width, bg.height - 100))
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
        labels_per_line = math.floor((v.width - 2 * gap) / (label_w + gap))
        left_margin = (v.width - labels_per_line * label_w_with_gap + gap) / 2
        line = math.floor(label_count / labels_per_line)
        column = label_count - line * labels_per_line

        l = ui.Label(
            text=title,
            background_color='grey',
            text_color='white',
            alignment=ui.ALIGN_CENTER,
            number_of_lines=0,
            frame=(
                left_margin + column * label_w_with_gap,
                gap + line * label_h_with_gap,
                label_w, label_h
            ))
        v.add_subview(l)
        return l


    tap_l = create_label('Tap')
    tap(tap_l, generic_handler)

    tap_2_l = create_label('Doubletap')
    doubletap(tap_2_l, generic_handler)

    long_l = create_label('Long press')
    long_press(long_l, long_press_handler)

    pan_l = create_label('Pan')
    pan(pan_l, pan_handler)

    swipe_l = create_label('Swipe (right)')
    swipe(swipe_l, generic_handler, direction=RIGHT)

    pinch_l = create_label('Pinch')
    pinch(pinch_l, pinch_handler)

    pan_or_pinch_l = create_label('Pan or pinch')
    pan(pan_or_pinch_l, pan_or_pinch_handler)
    pinch(pan_or_pinch_l, pan_or_pinch_handler)

    pan_or_swipe_l = create_label('Pan or swipe (right)')
    pan_r = pan(pan_or_swipe_l, pan_or_swipe_handler)
    swipe_r = swipe(pan_or_swipe_l, pan_or_swipe_handler, direction=RIGHT)
    swipe_r.before(pan_r)
    
    pan_and_pinch_l = create_label('Pan AND pinch')
    pan_r = pan(pan_and_pinch_l, pan_and_pinch_handler, 
        minimum_number_of_touches=2,
        maximum_number_of_touches=2)
    pinch_r = pinch(pan_and_pinch_l, pan_and_pinch_handler)
    pan_r.together_with(pinch_r)
