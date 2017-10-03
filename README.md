# Gestures for Pythonista
 
This is a convenience class for enabling gestures in Pythonista ui applications, including built-in views. Main intent here has been to make them Python friendly, hiding all the Objective-C stuff.

Get it from [GitHub](https://github.com/mikaelho/pythonista-gestures).

## Example

For example, do something when user swipes left on a TextView:
 
    def swipe_handler(view, data):
        print ‘I was swiped, starting from ‘ + str(data.location)
     
    tv = ui.TextView()
    Gestures().add_swipe(tv, swipe_handler, direction = Gestures.LEFT)

Your handler method gets two arguments, the `view` that received the gesture, and a `data` argument always contains the attributes described below. Individual gestures may provide more information; see the API documentation for the `add_` methods.
  
* `recognizer` - (ObjC) recognizer object
* `view` - (Pythonista) view that captured the object
* `location` - Location of the gesture as a `ui.Point` with `x` and `y` attributes
* `state` - State of gesture recognition; one of `Gestures.POSSIBLE/BEGAN/RECOGNIZED/CHANGED/ENDED/CANCELLED/FAILED`
* `number_of_touches` - Number of touches recognized

All of the `add_x` methods return a `recognizer` object that can be used to remove or disable the gesture as needed, see the API. You can also remove all gestures from a view with `remove_all_gestures(view)`.

# API

* [Class: Gestures](#class-gestures)
  * [Methods](#methods)


## Class: Gestures

## Methods


#### ` add_tap(self, view, action, number_of_taps_required = None, number_of_touches_required = None)`

  Call `action` when a tap gesture is recognized for the `view`.
  
  Additional parameters:
    
  * `number_of_taps_required` - Set if more than one tap is required for the gesture to be recognized.
  * `number_of_touches_required` - Set if more than one finger is required for the gesture to be recognized.

#### ` add_long_press(self, view, action, number_of_taps_required = None, number_of_touches_required = None, minimum_press_duration = None, allowable_movement = None)`

  Call `action` when a long press gesture is recognized for the `view`.
  
  Additional parameters:
    
  * `number_of_taps_required` - Set if more than one tap is required for the gesture to be recognized.
  * `number_of_touches_required` - Set if more than one finger is required for the gesture to be recognized.
  * `minimum_press_duration` - Set to change the default 0.5 second recognition treshold.
  * `allowable_movement` - Set to change the default 10 point maximum distance allowed for the gesture to be recognized.

#### ` add_pan(self, view, action, minimum_number_of_touches = None, maximum_number_of_touches = None)`

  Call `action` when a pan gesture is recognized for the `view`.
  
  Additional parameters:
    
  * `minimum_number_of_touches` - Set to control the gesture recognition.
  * `maximum_number_of_touches` - Set to control the gesture recognition.
  
  Handler `action` receives the following gesture-specific attributes in the `data` argument:
    
  * `translation` - Translation from the starting point of the gesture as a `ui.Point` with `x` and `y` attributes.
  * `velocity` - Current velocity of the pan gesture as points per second (a `ui.Point` with `x` and `y` attributes).

#### ` add_screen_edge_pan(self, view, action, edges)`

  Call `action` when a pan gesture starting from the edge is recognized for the `view`. `edges` must be set to one of `Gestures.EDGE_NONE/EDGE_TOP/EDGE_LEFT/EDGE_BOTTOM/EDGE_RIGHT/EDGE_ALL`. If you want to recognize pans from different edges, you have to set up separate recognizers with separate calls to this method.
  
  Handler `action` receives the same gesture-specific attributes in the `data` argument as pan gestures, see `add_pan`.

#### ` add_pinch(self, view, action)`

  Call `action` when a pinch gesture is recognized for the `view`.
  
  Handler `action` receives the following gesture-specific attributes in the `data` argument:
  
  * `scale` - Relative to the distance of the fingers as opposed to when the touch first started.
  * `velocity` - Current velocity of the pinch gesture as scale per second.

#### ` add_rotation(self, view, action)`

  Call `action` when a rotation gesture is recognized for the `view`.
  
  Handler `action` receives the following gesture-specific attributes in the `data` argument:
  
  * `rotation` - Rotation in radians, relative to the position of the fingers when the touch first started.
  * `velocity` - Current velocity of the rotation gesture as radians per second.

#### ` add_swipe(self, view, action, direction = None, number_of_touches_required = None)`

  Call `action` when a swipe gesture is recognized for the `view`.
  
  Additional parameters:
    
  * `direction` - Direction of the swipe to be recognized. Either one of `Gestures.RIGHT/LEFT/UP/DOWN`, or a list of multiple directions.
  * `number_of_touches_required` - Set if you need to change the minimum number of touches required.
  
  If swipes to multiple directions are to be recognized, the handler does not receive any indication of the direction of the swipe. Add multiple recognizers if you need to differentiate between the directions. 

#### ` disable(self, recognizer)`

  Disable a recognizer temporarily. 

#### ` enable(self, recognizer)`

  Enable a disabled gesture recognizer. There is no error if the recognizer is already enabled. 

#### ` remove(self, view, recognizer)`

  Remove the recognizer from the view permanently. 

#### ` remove_all_gestures(self, view)`

  Remove all gesture recognizers from a view. 


## Fine-tuning gesture recognition

By default only one gesture recognizer will be successful, but if you want to, for example, enable both zooming (pinch) and panning at the same time, allow both recognizers:

    g = Gestures()
    
    g.recognize_simultaneously = lambda gr, other_gr: gr == Gestures.PAN and other_gr == Gestures.PINCH
    
The other methods you can override are `fail` and `fail_other`, corresponding to the other [UIGestureRecognizerDelegate](https://developer.apple.com/reference/uikit/uigesturerecognizerdelegate?language=objc) methods.
    
All regular recognizers have convenience names that you can use like in the example above: `Gestures.TAP/PINCH/ROTATION/SWIPE/PAN/SCREEN_EDGE_PAN/LONG_PRESS`.

If you need to set these per gesture, instantiate separate `Gestures` objects.

## Notes
 
* To facilitate the gesture handler callbacks from Objective-C to Python, the Gestures instance used to create the gesture must be live. You do not need to manage that as objc_util.retain_global is used to keep a global reference around. If you for some reason must track the reference manually, you can turn this behavior off with a `retain_global_reference=False` parameter for the constructor.
* Single Gestures instance can be used to add any number of gestures to any number of views, but you can just as well create a new instance whenever and wherever you need to add a new handler.
* If you need to create millions of dynamic gestures in a long-running app, it can be worthwhile to explicitly `remove` them when no longer needed, to avoid a memory leak.

