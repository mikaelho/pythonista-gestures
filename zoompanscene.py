from scene import *
from Gestures import *

class ZoomPanScene(Scene):
    
  def setup(self):
    g = Gestures()
    g.add_pan(self.view, self.on_pan, maximum_number_of_touches=1)
    g.add_pinch(self.view, self.on_zoom)
    self.really_panning = False

    self.zoomer = Node(z_position=0.75, parent=self)
    self.content_area = Node(z_position=1.0, parent=self.zoomer)
  
  def on_pan(self, data):
    if data.state == Gestures.BEGAN:
      self.prev_location = data.location
      self.really_panning = True
    elif data.state == Gestures.CHANGED:
      self.pan(data)
    elif data.state == Gestures.ENDED:
      self.really_panning = False
    
  def pan(self, data):
    if data.number_of_touches < 2 and not self.really_panning: return 
    
    delta = data.location - self.prev_location
    delta.y = -delta.y
    self.prev_location = data.location
    self.content_area.position += delta/self.zoomer.scale
    
  def on_zoom(self, data):
    if data.state == Gestures.BEGAN:
      self.prev_location = data.location
      self.start_scale = self.zoomer.scale
    elif data.state == Gestures.CHANGED:
      scale = self.start_scale * data.scale
      scn_pos = data.location / self.zoomer.scale
      self.content_area.position -= scn_pos
      self.zoomer.scale = scale
      new_scn_pos = data.location/self.zoomer.scale
      self.content_area.position += new_scn_pos
    self.pan(data)
    
  def add_child(self, child):
    self.content_area.add_child(child)
    
if __name__ == '__main__':

  class SpaceScene(ZoomPanScene):
    
    def setup(self):
      super().setup()
      
      ship = SpriteNode('spc:PlayerShip1Orange')
      ship.position = self.size / 2
      self.add_child(ship)
      
      
  run(SpaceScene())


