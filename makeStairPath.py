# -*- coding: utf-8 -*-

import math
import os

import FreeCAD as App
import FreeCADGui
import Part
from PySide2 import QtCore
from PySide2.QtCore import QT_TRANSLATE_NOOP

from utils import *

# from importlib import reload
# import makeStairPath; reload(makeStairPath)

class StairPath:
    """turn a Shape or Sketch into a Shape representing the neutral line for the stairs"""
    def __init__(self, obj):
        """Initialize variables for the command that must exist at all times."""

        self.Type = 'StairPath'
        obj.addProperty("App::PropertyLength", "ele", "Stairs Geometry", "This is the total elevation from the top of the bottom landing to the top of the top landing").ele = 2000
        obj.addProperty("App::PropertyBool", "pathReversed", "Stairs Geometry", "reverse the path direction").pathReversed = False
        obj.addProperty("App::PropertyLink", "Base", "Stairs Geometry", "The base shape")

        obj.Proxy = self

    def skew(self,w,h,reversed):
        """Transform the edges of the base shape into a skewed set of edges for the "outgoing" shape.

        Currently, only two edge types are supported: lines and circles.
        Lines are transformed into lines, with a skew. Circles are transformed into a helix with a skew.

        The incoming shape is assumed to be flat.
        """
        def t(e,h0,h1):
            # print("e = {}".format(e.Curve))
            # print("fp = {} lp = {}\n".format(e.FirstParameter,e.LastParameter))
            if e.Curve.TypeId == "Part::GeomCircle":

                # print("e.Curve = {}".format(e.Curve))
                # print("curve.fp = {} curve.lp = {}\n".format(e.Curve.FirstParameter,e.Curve.LastParameter))
                pitch = (h1-h0)/(e.LastParameter-e.FirstParameter)*2*math.pi

                # print("make helix, pitch = {}, height = {}".format(pitch, h1-h0))

                lefthand = e.Curve.Axis.z < 0
                # print("lefthand ? {}".format(lefthand))
                hlx = Part.makeHelix(pitch, h1-h0, e.Curve.Radius, 0, lefthand)
                hlx.rotate(origin,e.Curve.Axis,360*e.FirstParameter/(2*math.pi))

                l = e.Curve.Location
                hlx.translate(App.Vector(l.x,l.y,h0))
                return hlx

            elif e.Curve.TypeId == "Part::GeomLine":
                vSkew = [v.Point for v in e.Vertexes]
                dh = (h1-h0)/(len(vSkew)-1)
                for i,v in enumerate(vSkew):
                    # print("v={}\n".format(v))
                    v.z = h0+i*dh

                return Part.makeLine(*vSkew)
            
            else:
                App.Console.PrintError("makeStairPath does not support {} in the base shape".format(e.Curve.TypeId))

        ne = []
        edgesIn = Part.__sortEdges__(w.Edges)
        length = sum([x.Length for x in edgesIn])

        if not reversed:
            h0 = edgesIn[0].valueAt(edgesIn[0].FirstParameter).z
            pitch = h/length
        else:
            h0 = edgesIn[0].valueAt(edgesIn[0].FirstParameter).z+h
            pitch = -h/length

        for e in edgesIn:
            h1 = h0+pitch*e.Length
            # print("edge segment h0={}, h1={}, curve={}".format(h0,h1,e.Curve))
            x = t(e,h0,h1)
            ne.append(x)
            h0 = h1

#        return Part.Compound([Part.Wire(l) for l in ne])
        return Part.Wire(ne)

    def execute(self, obj):
        """Print a short message when doing a recomputation, this method is mandatory"""

        obj.Shape = self.skew(obj.Base.Shape,obj.ele.getValueAs("mm"),obj.pathReversed)
        return

    def __getstate__(self):
        """
        Called during document saving.
        """
        return self.Type

    def __setstate__(self,state):
        """
        Called during document restore.
        """
        if state:
            self.Type = state

class ViewProviderStairPath:
    def __init__(self,vobj):
        vobj.Proxy = self

        self._check_attr()
        dirname = os.path.dirname(__file__)
        self.icon_fn = os.path.join(dirname, "resources", "icons", "makeStairsPath.svg")

    def attach(self, vobj):
        """Called to attach viewprovider to object"""
        self.Object = vobj.Object

    def claimChildren(self):
        c = []
        if hasattr(self,"Object"):
            if hasattr(self.Object,"Base") and self.Object.Base is not None:
                c.append(self.Object.Base)
        return c

    def _check_attr(self):
        ''' Check for missing attributes. '''
        if not hasattr(self, "icon_fn"):
            setattr(self, "icon_fn", os.path.join(os.path.dirname(__file__), "resources", "icons", "makeStairsPath.svg"))

    def __getstate__(self):
        """
        Called during document saving.

        At minimum, an empty implementation is necessary to support proper
        serialization.
        """
        return None

    def __setstate__(self,state):
        """
        Called during document restore.

        At minimum, an empty implementation is necessary to support proper
        serialization.
        """
        pass

    def getIcon(self):
        self._check_attr()
        return self.icon_fn

class makeStairPath:
    """turn a path or sketch into a path representing the neutral line"""

    def Activated(self):
        """Run the following code when the command is activated (button press)."""

        obj = App.ActiveDocument.addObject("Part::FeaturePython", "StairPath")
        StairPath(obj)

        if App.GuiUp:
            ViewProviderStairPath(obj.ViewObject)

        sel = FreeCADGui.Selection.getSelection() # " sel " contains the items selected
        obj.Base = sel[0]

        obj.touch()
        
        App.ActiveDocument.recompute()

    def IsActive(self):
        return len(FreeCADGui.Selection.getSelection())>0

    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""

        MenuText = QtCore.QT_TRANSLATE_NOOP("genericStairs","make stairs")
        ToolTip = QtCore.QT_TRANSLATE_NOOP("genericStairs","make stairs")

        rel_path = "Mod/stairs2/Resources/icons/makeStairsPath.svg"
        path = App.getHomePath() + rel_path

        import os
        if not os.path.exists(path):
            path =  App.getUserAppDataDir() + rel_path

        return {'Pixmap': path,
                'MenuText': MenuText,
                'ToolTip': ToolTip}

# The command must be "registered" with a unique name by calling its class.
FreeCADGui.addCommand('makeStairPath', makeStairPath())
