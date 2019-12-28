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
* `began`, `changed`, `ended` - convenience boolean properties to check for these states
* `number_of_touches` - Number of touches recognized

For continuous gestures, check for `data.ended` in the handler if you are just interested that a pinch or a force press happened.

All of the `add_x` methods return a `recognizer` object that can be used to remove or disable the gesture as needed, see the API. You can also remove all gestures from a view with `remove_all_gestures(view)`.

# API

* [Class: Gestures](#class-gestures)
  * [Methods](#methods)


## Class: Gestures

## Methods


#### `add_tap(self, view, action, number_of_taps_required = None, number_of_touches_required = None)`

  Call `action` when a tap gesture is recognized for the `view`.
  
  Additional parameters:
    
  * `number_of_taps_required` - Set if more than one tap is required for the gesture to be recognized.
  * `number_of_touches_required` - Set if more than one finger is required for the gesture to be recognized.

#### `add_doubletap(self, view, action, number_of_touches_required = None)`

  Convenience method that calls `add_tap` with a 2-tap requirement. 

#### `add_long_press(self, view, action, number_of_taps_required = None, number_of_touches_required = None, minimum_press_duration = None, allowable_movement = None)`

  Call `action` when a long press gesture is recognized for the `view`. Note that this is a continuous gesture; you might want to check for `data.state == Gestures.CHANGED` or `ENDED` to get the desired results.
  
  Additional parameters:
    
  * `number_of_taps_required` - Set if more than one tap is required for the gesture to be recognized.
  * `number_of_touches_required` - Set if more than one finger is required for the gesture to be recognized.
  * `minimum_press_duration` - Set to change the default 0.5 second recognition treshold.
  * `allowable_movement` - Set to change the default 10 point maximum distance allowed for the gesture to be recognized.

#### `add_pan(self, view, action, minimum_number_of_touches = None, maximum_number_of_touches = None)`

  Call `action` when a pan gesture is recognized for the `view`. This is a continuous gesture.
  
  Additional parameters:
    
  * `minimum_number_of_touches` - Set to control the gesture recognition.
  * `maximum_number_of_touches` - Set to control the gesture recognition.
  
  Handler `action` receives the following gesture-specific attributes in the `data` argument:
    
  * `translation` - Translation from the starting point of the gesture as a `ui.Point` with `x` and `y` attributes.
  * `velocity` - Current velocity of the pan gesture as points per second (a `ui.Point` with `x` and `y` attributes).

#### `add_screen_edge_pan(self, view, action, edges)`

  Call `action` when a pan gesture starting from the edge is recognized for the `view`. This is a continuous gesture.
  
  `edges` must be set to one of `Gestures.EDGE_NONE/EDGE_TOP/EDGE_LEFT/EDGE_BOTTOM/EDGE_RIGHT/EDGE_ALL`. If you want to recognize pans from different edges, you have to set up separate recognizers with separate calls to this method.
  
  Handler `action` receives the same gesture-specific attributes in the `data` argument as pan gestures, see `add_pan`.

#### `add_pinch(self, view, action)`

  Call `action` when a pinch gesture is recognized for the `view`. This is a continuous gesture.
  
  Handler `action` receives the following gesture-specific attributes in the `data` argument:
  
  * `scale` - Relative to the distance of the fingers as opposed to when the touch first started.
  * `velocity` - Current velocity of the pinch gesture as scale per second.

#### `add_rotation(self, view, action)`

  Call `action` when a rotation gesture is recognized for the `view`. This is a continuous gesture.
  
  Handler `action` receives the following gesture-specific attributes in the `data` argument:
  
  * `rotation` - Rotation in radians, relative to the position of the fingers when the touch first started.
  * `velocity` - Current velocity of the rotation gesture as radians per second.

#### `add_swipe(self, view, action, direction = None, number_of_touches_required = None)`

  Call `action` when a swipe gesture is recognized for the `view`.
  
  Additional parameters:
    
  * `direction` - Direction of the swipe to be recognized. Either one of `Gestures.RIGHT/LEFT/UP/DOWN`, or a list of multiple directions.
  * `number_of_touches_required` - Set if you need to change the minimum number of touches required.
  
  If swipes to multiple directions are to be recognized, the handler does not receive any indication of the direction of the swipe. Add multiple recognizers if you need to differentiate between the directions. 

#### `add_force_press(self, view, action, threshold=0.4)`

  Call `action` when a force press gesture is recognized for the `view`. This is a continuous gesture.
  
  Additional parameters:
    
  * `threshold` - How much pressure is required for the gesture to be detected, between 0 and 1. Default is 0.4.
  
  Handler `action` receives the following gesture-specific attributes in the `data` argument:
  
  * `force` - Force of the press, a value between `threshold` and 1.

#### `disable(self, recognizer)`

  Disable a recognizer temporarily. 

#### `enable(self, recognizer)`

  Enable a disabled gesture recognizer. There is no error if the recognizer is already enabled. 

#### `remove(self, view, recognizer)`

  Remove the recognizer from the view permanently. 

#### `remove_all_gestures(self, view)`

  Remove all gesture recognizers from a view. 

#### `disable_swipe_to_close(cls, view)`
`@classmethod`

  Utility class method that will
  disable the two-finger-swipe-down gesture
  used in Pythonista to end the program
  when in full screen view 
  (`hide_title_bar` set to `True`).


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

