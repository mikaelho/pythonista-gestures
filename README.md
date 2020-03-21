# gestures

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

# API

* [Functions](#functions)
  * [Gestures](#gestures)
  * [Gesture management](#gesture-management)
  * [Drag and drop](#drag-and-drop)


# Functions


#### GESTURES
#### `tap(view, action,number_of_taps_required=None, number_of_touches_required=None)`

  Call `action` when a tap gesture is recognized for the `view`.
  
  Additional parameters:
  
  * `number_of_taps_required` - Set if more than one tap is required for
    the gesture to be recognized.
  * `number_of_touches_required` - Set if more than one finger is
    required for the gesture to be recognized.

#### `doubletap(view, action,number_of_touches_required=None)`

  Convenience method that calls `tap` with a 2-tap requirement.
      

#### `long_press(view, action,number_of_taps_required=None,number_of_touches_required=None,minimum_press_duration=None,allowable_movement=None)`

  Call `action` when a long press gesture is recognized for the
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

#### `pan(view, action,minimum_number_of_touches=None,maximum_number_of_touches=None)`

  Call `action` when a pan gesture is recognized for the `view`.
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

#### `edge_pan(view, action, edges)`

  Call `action` when a pan gesture starting from the edge is
  recognized for the `view`. This is a continuous gesture.
  
  `edges` must be set to one of
  `gestures.EDGE_NONE/EDGE_TOP/EDGE_LEFT/EDGE_BOTTOM/EDGE_RIGHT
  /EDGE_ALL`. If you want to recognize pans from different edges,
  you have to set up separate recognizers with separate calls to this
  method.
  
  Handler `action` receives the same gesture-specific attributes in
  the `data` argument as pan gestures, see `pan`.

#### `pinch(view, action)`

  Call `action` when a pinch gesture is recognized for the `view`.
  This is a continuous gesture.
  
  Handler `action` receives the following gesture-specific attributes
  in the `data` argument:
  
  * `scale` - Relative to the distance of the fingers as opposed to when
    the touch first started.
  * `velocity` - Current velocity of the pinch gesture as scale
    per second.

#### `rotation(view, action)`

  Call `action` when a rotation gesture is recognized for the `view`.
  This is a continuous gesture.
  
  Handler `action` receives the following gesture-specific attributes
  in the `data` argument:
  
  * `rotation` - Rotation in radians, relative to the position of the
    fingers when the touch first started.
  * `velocity` - Current velocity of the rotation gesture as radians
    per second.

#### `swipe(view, action,direction=None,number_of_touches_required=None,min_distance=None,max_distance=None)`

  Call `action` when a swipe gesture is recognized for the `view`.
  
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

#### GESTURE MANAGEMENT
#### `disable(handler)`

  Disable a recognizer temporarily. 

#### `enable(handler)`

  Enable a disabled gesture recognizer. There is no error if the
  recognizer is already enabled. 

#### `remove(view, handler)`

  Remove the recognizer from the view permanently. 

#### `remove_all_gestures(view)`

  Remove all gesture recognizers from a view. 

#### `disable_swipe_to_close(view)`

  Utility class method that will disable the two-finger-swipe-down
  gesture used in Pythonista to end the program when in full screen
  view (`hide_title_bar` set to `True`).
  
  Returns a tuple of the actual ObjC view and dismiss target.

#### `replace_close_gesture(view, recognizer_class)`


#### DRAG AND DROP
#### `drag(view, payload, allow_others=False)`

  Sets the `view` to be the sender in a drag and drop operation. Dragging
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

#### `drop(view, action, accept=None)`

  Sets the `view` as a drop target, calling the `action` function with
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
