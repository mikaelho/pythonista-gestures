# coding: utf-8

"""
Gestures wrapper for iOS

# Gestures for the Pythonista iOS app
 
This is a convenience class for enabling gestures, including drag and drop
support, in Pythonista UI applications. Main intent here has been to make
them Python friendly, hiding all the Objective-C details.

Run the file on its own to see a demo of the supported gestures.

![Demo image](https://raw.githubusercontent.com/mikaelho/pythonista-gestures/master/gestures.jpg)

## Installation

Copy from [GitHub](https://github.com/mikaelho/pythonista-gestures), or

    pip install pythonista-gestures

with [stash](https://github.com/ywangd/stash).

## Versions:

* 1.2 - Adds drag and drop support.  
* 1.1 - Adds distance parameters to swipe gestures.
* 1.0 - First version released to PyPi. 
  Breaks backwards compatibility in syntax, adds multi-recognizer coordination,
  and removes force press support.

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

## Drag and drop

This module supports dragging and dropping both within a Pythonista app and
between Pythonista and another app (only possible on iPads). These two cases
are handled differently:
    
* For in-app drops, Apple method of relaying objects is skipped completely,
  and you can refer to _any_ Python object to be dropped to the target view.
* For cross-app drops, we have to conform to Apple method of managing data.
  Currently only plain text and image drops are supported, in either direction.
* It is also good to note that `ui.TextField` and `ui.TextView` views natively
  act as receivers for both in-app and cross-app plain text drag and drop.

View is set to be a sender for a drap and drop operation with the `drag`
function. Drag starts with a long press, and can end in any view that has been
set as a receiver with the `drop` function. Views show the readiness to receive
data with a green "plus" sign. You can accept only specific types of data;
incompatible drop targets show a grey "forbidden" sign.

Following example covers setting up an in-app drag and drop operation between
two labels. To repeat, in the in-app case, the simple string could replaced by
any Python object of any complexity, passed by reference:
    
    drag(sender_label, "Important data")
    
    drop(receiver_label,
        lambda data, sender, receiver: setattr(receiver, 'text', data),
        accept=str)

See the documentation for the two functions for details.

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
"""

__version__ = '1.2.1'

import ctypes
import functools
import inspect
import os
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

#  Drag and drop classes

NSItemProvider = ObjCClass('NSItemProvider')
UIDragItem = ObjCClass('UIDragItem')
UIDragInteraction = ObjCClass('UIDragInteraction')
UIDropInteraction = ObjCClass('UIDropInteraction')
UIDropProposal = ObjCClass('UIDropProposal')
NSItemProvider = ObjCClass('NSItemProvider')
UIImagePNGRepresentation = c.UIImagePNGRepresentation
UIImagePNGRepresentation.restype = c_void_p
UIImagePNGRepresentation.argtypes = [c_void_p]

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
    (docgen-ignore)
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
            
            
class ObjCPlus:
    """ docgen-ignore """
    
    def __new__(cls, *args, **kwargs):
        objc_class = getattr(cls, '_objc_class', None)
        if objc_class is None:
            objc_class_name = cls.__name__ + '_ObjC'
            objc_superclass = getattr(
                cls, '_objc_superclass', NSObject)
            objc_debug = getattr(cls, '_objc_debug', True)
            
            #'TempClass_'+str(uuid.uuid4())[-12:]
            
            objc_methods = []
            objc_classmethods = []
            for key in cls.__dict__:
                value = getattr(cls, key)
                if (inspect.isfunction(value) and 
                    '_self' in inspect.signature(value).parameters
                ):
                    if getattr(value, '__self__', None) == cls:
                        objc_classmethods.append(value)
                    else:
                        objc_methods.append(value)
            if ObjCDelegate in cls.__mro__:
                objc_protocols = cls.__name__
            else:
                objc_protocols = getattr(cls, '_objc_protocols', [])
            if not type(objc_protocols) is list:
                objc_protocols = [objc_protocols]
            cls._objc_class = objc_class = create_objc_class(
                objc_class_name,
                superclass=objc_superclass,
                methods=objc_methods,
                classmethods=objc_classmethods,
                protocols=objc_protocols,
                debug=objc_debug
            )
        
        instance = objc_class.alloc().init()

        for key in dir(cls):
            value = getattr(cls, key)
            if inspect.isfunction(value):
                if (not key.startswith('__') and 
                not '_self' in inspect.signature(value).parameters):
                    setattr(instance, key, types.MethodType(value, instance))
                if key == '__init__':
                    value(instance, *args, **kwargs)

        return instance

        
class ObjCDelegate(ObjCPlus):
    """ If you inherit from this class, the class name must match the delegate 
    protocol name. (docgen-ignore) """
            
            
def _is_objc_type(objc_instance, objc_class):
    return objc_instance.isKindOfClass_(objc_class.ptr)


class UIGestureRecognizerDelegate(ObjCDelegate):
    """ docgen-ignore """
    
    def __init__(self, recognizer_class, view, handler_func):
        self.view = view
        self.handler_func = handler_func
        self.other_recognizers = []
        
        view.touch_enabled = True

        if handler_func == 'close':
            self.recognizer = replace_close_gesture(view, recognizer_class)
        else:
            self.recognizer = recognizer_class.alloc().initWithTarget_action_(
                self, 'gestureAction').autorelease()
            view.objc_instance.addGestureRecognizer_(self.recognizer)

        retain_global(self)
    
    def gestureAction(_self, _cmd):
        self = ObjCInstance(_self)
        view = self.view
        recognizer = self.recognizer
        handler_func = self.handler_func
        data = Data()
        data.recognizer = recognizer
        data.view = view
        location = recognizer.locationInView_(view.objc_instance)
        data.location = ui.Point(location.x, location.y)
        data.state = recognizer.state()
        data.number_of_touches = recognizer.numberOfTouches()
        
        if (_is_objc_type(recognizer, UIPanGestureRecognizer) or 
        _is_objc_type(recognizer, UIScreenEdgePanGestureRecognizer)):
            trans = recognizer.translationInView_(ObjCInstance(view))
            vel = recognizer.velocityInView_(ObjCInstance(view))
            data.translation = ui.Point(trans.x, trans.y)
            data.velocity = ui.Point(vel.x, vel.y)
        elif _is_objc_type(recognizer, UIPinchGestureRecognizer):
            data.scale = recognizer.scale()
            data.velocity = recognizer.velocity()
        elif _is_objc_type(recognizer, UIRotationGestureRecognizer):
            data.rotation = recognizer.rotation()
            data.velocity = recognizer.velocity()
    
        handler_func(data)
        
    def gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer_(
            _self, _sel, _gr, _other_gr):
        self = ObjCInstance(_self)
        other_gr = ObjCInstance(_other_gr)
        return other_gr in self.other_recognizers
        
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

        
#docgen: Gestures

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
    handler = UIGestureRecognizerDelegate(UITapGestureRecognizer, view, action)

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
    handler = UIGestureRecognizerDelegate(UILongPressGestureRecognizer, view, action)

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
    handler = UIGestureRecognizerDelegate(UIPanGestureRecognizer, view, action)

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
    handler = UIGestureRecognizerDelegate(UIScreenEdgePanGestureRecognizer, view, action)

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
    handler = UIGestureRecognizerDelegate(UIPinchGestureRecognizer, view, action)

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
    handler = UIGestureRecognizerDelegate(UIRotationGestureRecognizer, view, action)

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
    handler = UIGestureRecognizerDelegate(UISwipeGestureRecognizer, view, action)

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


#docgen: Gesture management

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


# Drag and drop delegates

drag_and_drop_prefix = 'py_object_'

def _to_pyobject(item):
    item = ObjCInstance(item)
    try:
        data = item.localObject()
        if data is None: return None
        if not str(data).startswith(drag_and_drop_prefix):
            return None
        address_str = str(data)[len(drag_and_drop_prefix):]
        address = int(address_str)
        result = ctypes.cast(address, ctypes.py_object).value
        return result
    except Exception as e:
        return None


class UIDragInteractionDelegate(ObjCDelegate):
    """ docgen-ignore """
    
    def __init__(self, view, data, allow_others):
        if not callable(data):
            data = functools.partial(lambda d, sender: d, data)
        self.data = { 'payload_func': data }
        self.view = view
        view.touch_enabled = True
        draginteraction = UIDragInteraction.alloc().initWithDelegate_(self)
        draginteraction.setEnabled(True)
        draginteraction.setAllowsSimultaneousRecognitionDuringLift_(allow_others)
        view.objc_instance.addInteraction(draginteraction)
            
        retain_global(self)
    
    def dragInteraction_itemsForBeginningSession_(_self, _cmd,
    _interaction, _session):
        self = ObjCInstance(_self)
        session = ObjCInstance(_session)
        payload = self.data['payload_func'](self.view)
        # Retain reference to potentially ephemeral data
        
        self.content_actual = {
            'payload': payload,
            'sender': self.view
        }
        
        external_payload = ''
        
        if type(payload) is str:
            external_payload = payload
        elif type(payload) in [ui.Image]:
            external_payload = ObjCInstance(payload)
        provider = NSItemProvider.alloc().initWithObject(external_payload)
        item = UIDragItem.alloc().initWithItemProvider(provider)
        item.setLocalObject_(
            str(drag_and_drop_prefix) +  
            str(id(self.content_actual)))
        object_array = NSArray.arrayWithObject(item)
        return object_array.ptr
   

class UIDropInteractionDelegate(ObjCDelegate):
    """ docgen-ignore """
    
    def __init__(self, view, handler_func, accept=None):
        self.accept_type = None
        if type(accept) is type:
            if accept is str:
                self.accept_type = NSString
            elif accept is ui.Image:
                self.accept_type = UIImage
            accept = functools.partial(
                lambda dtype, d, s, r: type(d) is dtype, accept)
        self.functions = {
            'handler': handler_func,
            'accept': accept
        }
        self.view = view
        view.touch_enabled = True
        
        dropinteraction = UIDropInteraction.alloc().initWithDelegate_(self)
        view.objc_instance.addInteraction(dropinteraction)
        retain_global(self)
        
    def dropInteraction_canHandleSession_(_self, _cmd, _interaction, _session):
        return True
        
    def dropInteraction_sessionDidUpdate_(_self, _cmd, _interaction, _session):
        self = ObjCInstance(_self)
        session = ObjCInstance(_session)
        proposal = 2 # UIDropOperationCopy
        accept_func = self.functions['accept']

        if session.localDragSession():
            if accept_func is not None:
                for item in session.items():
                    data = _to_pyobject(item)
                    payload = data['payload']
                    sender = data['sender']
                    if not accept_func(payload, sender, self.view):
                        proposal = 1 # UIDropOperationForbidden
        else:
            if (self.accept_type is None or
            not session.canLoadObjectsOfClass(self.accept_type)):
                    proposal = 1 # UIDropOperationForbidden

        return UIDropProposal.alloc().initWithDropOperation(proposal).ptr
        
    def dropInteraction_performDrop_(_self, _cmd, _interaction, _session):
        self = ObjCInstance(_self)
        session = ObjCInstance(_session)
        handler = self.functions['handler']
        
        if session.localDragSession():
            for item in session.items():
                data = _to_pyobject(item)
                payload = data['payload']
                sender = data['sender']
                handler(payload, sender, self.view)
        else:
            if self.accept_type is not None:
                
                def completion_handler(_cmd, _object, _error):
                    obj = ObjCInstance(_object)
                    payload = None
                    if _is_objc_type(obj, NSString):
                        payload = str(obj)
                    elif _is_objc_type(obj, UIImage):
                        payload = ui.Image.from_data(uiimage_to_png(obj))
                    handler(payload, None, self.view)
                handler_block = ObjCBlock(
                    completion_handler, restype=None,
                    argtypes=[c_void_p, c_void_p, c_void_p])
                retain_global(handler_block)
                
                for item in session.items():
                    provider = item.itemProvider()
                    provider.loadObjectOfClass_completionHandler_(
                        self.accept_type, handler_block)
                    break

#docgen: Drag and drop                                
        
@on_main_thread
def drag(view, payload, allow_others=False):
    """ Sets the `view` to be the sender in a drag and drop operation. Dragging
    starts with a long press.
    
    For within-app drag and drop, `payload` can be anything, and it is passed
    by reference.
    
    If the `payload` is a text string or a `ui.Image`, it can be dragged
    (copied) to another app (on iPad).
    There is also built-in support for dropping text to any `ui.TextField` or
    `ui.TextView`. 
    
    If `payload` is a function, it is called at the time when the drag starts.
    The function receives one argument, the sending `view`, and must return the
    data to be dragged.

    Additional parameters:

    * `allow_others` - Set to True if other gestures attached to the view
    should be prioritized over the dragging.
    """
    
    UIDragInteractionDelegate(view, payload, allow_others)
    
@on_main_thread
def drop(view, action, accept=None):
    """ Sets the `view` as a drop target, calling the `action` function with
    dropped data.
    
    Additional parameters:

    * `accept` - Control which data will be accepted for dropping. Simplest
    option is to provide an accepted Python type like `dict` or `ui.Label`.
    
      For cross-app drops, only two types are currently supported: `str` for
      plain text, and `ui.Image` for images.
      
      For in-app drops, the `accept` argument can also be a function that will
      be called when a drag enters the view. Function gets same parameters
      as the main handler, and should return False if the view should not accept
      the drop.
    
    `action` function has to have this signature:
        
        def handle_drop(data, sender, receiver):
            ...
            
    Arguments of the `action` function are:
            
    * `data` - The dragged data.
    * `sender` - Source view of the drag and drop. This is `None` for drags
    between apps.
    * `receiver` - Same as `view`.
    """
    
    UIDropInteractionDelegate(view, action, accept)


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

    def create_label(title, instance=None):
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

        if instance is None:
            instance = ui.Label(
                text=title,
                background_color='grey',
                text_color='white',
                alignment=ui.ALIGN_CENTER,
                number_of_lines=0
            )
        
        instance.frame = (
            left_margin + column * label_w_with_gap,
            gap + line * label_h_with_gap,
            label_w, label_h
        )
        v.add_subview(instance)
        return instance


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
 
    drag_dict_l = create_label('Drag dict')
    drag_image_l = create_label('Drag image')
    drop_dict_l = create_label('Drop dict')
    iv = ui.ImageView(
        image=ui.Image('iow:image_32'),
        background_color='grey',
        content_mode=ui.CONTENT_CENTER,
    )
    iv.objc_instance.setClipsToBounds_(True)
    drop_image_l = create_label('Image drop', iv)
 
    drag(drag_dict_l, {'message': 'Success'})
    
    drag(drag_image_l, ui.Image('iow:ios7_checkmark_32'))
    
    def dict_dropped(data, sender, receiver):
        receiver.text = f"Drop\n{data['message']}"
        ui.delay(lambda: setattr(receiver, 'text', 'Drop'), 2.0)

    drop(drop_dict_l, dict_dropped, accept=dict)
    
    def image_dropped(data, sender, receiver):
        receiver.image = data
        ui.delay(lambda:
            setattr(receiver, 'image', ui.Image('iow:image_24')),
            2.0
        )
        
    drop(drop_image_l, image_dropped, accept=ui.Image)
