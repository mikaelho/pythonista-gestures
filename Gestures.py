# coding: utf-8
import ui
from objc_util import *
import uuid

# https://developer.apple.com/library/prerelease/ios/documentation/UIKit/Reference/UIGestureRecognizer_Class/index.html#//apple_ref/occ/cl/UIGestureRecognizer

class Gestures():
	
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
	
	def __init__(self, retain_global_reference = True):
		self.buttons = {}
		self.views = {}
		self.recognizers = {}
		self.actions = {}
		
		if retain_global_reference:
			retain_global(self)
		
	def add_tap(self, view, action, number_of_taps_required = None, number_of_touches_required = None):
		recog = self._get_recog('UITapGestureRecognizer', view, self._general_action, action)
		
		if number_of_taps_required: 
			recog.numberOfTapsRequired = number_of_taps_required
		if number_of_touches_required:
			recog.numberOfTouchesRequired = number_of_touches_required
			
		return recog
	
	def add_long_press(self, view, action, number_of_taps_required = None, number_of_touches_required = None, minimum_press_duration = None, allowable_movement = None):
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

	def add_pan(self, view, action, minimum_number_of_touches = None, maximum_number_of_touches = None, set_translation = None):
		recog = self._get_recog('UIPanGestureRecognizer', view, self._pan_action, action)
		
		if minimum_number_of_touches:
			recog.minimumNumberOfTouches = minimum_number_of_touches
		if maximum_number_of_touches:
			recog.maximumNumberOfTouches = maximum_number_of_touches
		if set_translation:
			recog.set_translation_(CGPoint(set_translation.x, set_translation.y), ObjCInstance(view))
			
		return recog
			
	def add_screen_edge_pan(self, view, action, edges = None):
		recog = self._get_recog('UIScreenEdgePanGestureRecognizer', view, self._pan_action, action)
		
		if edges:
			recog.edges = edges
		
		return recog
		
	def add_pinch(self, view, action):
		recog = self._get_recog('UIPinchGestureRecognizer', view, self._pinch_action, action)
		
		return recog
		
	def add_rotation(self, view, action):
		recog = self._get_recog('UIRotationGestureRecognizer', view, self._rotation_action, action)
		
		return recog

	def add_swipe(self, view, action, direction = None, number_of_touches_required = None):		
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
			
	def remove(self, view, recognizer):
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
		
	def enable(self, recognizer):
		ObjCInstance(recognizer).enabled = True
		
	def disable(self, recognizer):
		ObjCInstance(recognizer).enabled = False
		
	def remove_all_gestures(self, view):
		gestures = ObjCInstance(view).gestureRecognizers()
		for recog in gestures:
			self.remove(view, recog)
	
	def _get_recog(self, recog_name, view, internal_action, final_handler):
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
		return recognizer
	
	def _context(self, button):
		key = button.name
		return (self.views[key], self.recognizers[key], self.actions[key])
		
	def _location(self, view, recog):
		loc = recog.locationInView_(ObjCInstance(view))
		return ui.Point(loc.x, loc.y)
		
	def _general_action(self, sender):
		(view, recog, action) = self._context(sender)
		location = self._location(view, recog)
		action(view, location)
		
	def _pan_action(self, sender):
		(view, recog, action) = self._context(sender)
		location = self._location(view, recog)
		trans = recog.translationInView_(ObjCInstance(view))
		vel = recog.velocityInView_(ObjCInstance(view))
		
		translation = ui.Point(trans.x, trans.y)
		velocity = ui.Point(vel.x, vel.y)
		
		action(view, location, translation, velocity)
		
	def _pinch_action(self, sender):
		(view, recog, action) = self._context(sender)
		location = self._location(view, recog)
		action(view, location, recog.scale(), recog.velocity())
		
	def _rotation_action(self, sender):
		(view, recog, action) = self._context(sender)
		location = self._location(view, recog)
		action(view, location, recog.rotation(), recog.velocity())

# TESTING AND DEMONSTRATION

if __name__ == "__main__":

	class EventDisplay(ui.View):
		def __init__(self):
			self.tv = ui.TextView(flex='WH')
			self.add_subview(self.tv)
			self.tv.frame = (0, 0, self.width, self.height)
			
			g = Gestures()
			
			g.add_tap(self.tv, self.general_handler)
			
			g.add_long_press(self.tv, self.general_handler)
			
			# Pan disabled to test the function and to see swipe working
			pan = g.add_pan(self.tv, self.pan_handler)
			g.disable(pan)
			
			g.add_screen_edge_pan(self.tv, self.pan_handler, edges = Gestures.EDGE_LEFT)
			
			g.add_swipe(self.tv, self.general_handler, direction = [Gestures.LEFT, Gestures.RIGHT])
			
			g.add_pinch(self.tv, self.pinch_handler)
			
			g.add_rotation(self.tv, self.rotation_handler)
			
		def t(self, msg):
			self.tv.text = self.tv.text + msg + '\n'

		def general_handler(self, view, start_location):
			self.t('General: ' + str(start_location))
			
		def pan_handler(self, view, location, translation, velocity):
			self.t('Pan: ' + str(translation))
			
		def pinch_handler(self, view, touch_center, scale, velocity):
			self.t('Pinch: ' + str(scale))
			
		def rotation_handler(self, view, touch_center, rotation, velocity):
			self.t('Rotation: ' + str(rotation))
		
	view = EventDisplay()
	view.present()