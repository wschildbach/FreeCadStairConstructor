# -*- coding: utf-8 -*-

import os
import PySide2
from PySide2 import QtCore

import FreeCAD as App

import Draft, Part, FreeCAD, math, PartGui, FreeCADGui, numpy, itertools
from FreeCAD import Base, Console
import functools

from PySide2.QtCore import QT_TRANSLATE_NOOP

import utils

# https://www.blocksrvt.com/post/stair-calculation

# reminder: for debugging
# from importlib import reload; import makeStairs; reload(makeStairs)

class genericStairs:
    """make a set of stairs"""

    def __init__(self,obj):
        """Initialize variables for the command that must exist at all times."""

        self.Type = "stairs"

        obj.addProperty("App::PropertyInteger","nRisers" ,"Steps" ,"number of steps" ).nRisers=10
        obj.addProperty("App::PropertyLength","treadThickness","Steps" ,"thickness of tread" ).treadThickness=30
        obj.addProperty("App::PropertyLength","treadWidth","Stairs" ,"width of tread" ).treadWidth=3000
        obj.addProperty("App::PropertyLength","treadNosing","Steps" ,"nosing of tread" ).treadNosing=30
        obj.addProperty("App::PropertyEnumeration","railType","Rails" ,"display rails" ).railType=["None","Left","Right","Both"]
        obj.addProperty("App::PropertyLength","railDia","Rails" ,"diameter of rails" ).railDia=40

        obj.addProperty("App::PropertyLink","Base" ,"Stairs" ,"Wire representing the neutral line of the stairs" ).Base = None
        obj.addProperty("App::PropertyLinkList","Objects" ,"Stairs" ,"Hand rails" ).Objects = []

        obj.addProperty("App::PropertyLink","housing" ,"Stairs" ,"Stair housing" ).housing = None
        obj.addProperty("App::PropertyBool","hasSupport" ,"Stairs" ,"Add support beam" ).hasSupport = False

        obj.Proxy=self

        self.wire = None
        self.e = None
        self.flip = 1
        self.val = []

    def execute(self, obj):
        """Print a short message when doing a recomputation, this method is mandatory"""

        self.wire = obj.Base.Shape
        self.e = utils.multiEdge(self.wire)
        # helper array for parameter taps
        self.val = numpy.linspace(self.e.FirstParameter,self.e.LastParameter,obj.nRisers+1)
        dz = self.e.valueAt(self.val[-1]).z - self.e.valueAt(self.val[0]).z
        slope = abs(dz)/(self.e.LastParameter - self.e.FirstParameter)

        # make sure we always follow the path uphill
        if dz > 0:
            self.flip = 1
        else:
            print("shape is flipped\n")
            self.flip = -1
            self.val = self.val[::-1] # run parameter backwards

        mm = App.Units.parseQuantity("1 mm")
        sh = self.makeStairs(obj.nRisers, 0*mm, obj.treadThickness, 0*mm, obj.treadWidth, obj.treadNosing)

        # print("objects before={}".format(obj.Objects))
        for o in obj.Objects:
            # print("removing {}".format(o.Name))
            App.ActiveDocument.removeObject(o.Name)
        obj.Objects = []
        c=[]

        if obj.hasSupport:
            rectangle = Draft.make_rectangle(100, 120, None, True)
            sw = self.makeSupport(obj, utils.origin, rectangle)
            print("makesuport returned {}".format(sw))
            c.append(sw)
            print("objects after 01={}".format(c))

        obj.Objects = c
        print("objects after={}".format(obj.Objects))

        if sh is not None:
            if obj.housing is not None and hasattr(obj.housing,'Shape'):
                sh = obj.housing.Shape.common(sh)
            obj.Shape = sh

    def makeSupport(self, obj, offset, profile):
        """given a profile, sweep that profile along the stairpath, and offset by offset
        
        If no profile is given, a circle 40mm dia is used by default
        Vector offset
        Shape profile
        """

        def r2d(x):
            return 360*x/(2*math.pi)

        if profile is None:
            profile = App.ActiveDocument.addObject("Part::Circle")
            profile.Radius = 20
            profile.Angle1 = 0
            profile.Angle2 = 360

        pos = self.e.valueAt(self.val[0])
        direct = self.e.tangentAt(self.val[0])
        yaw = r2d(math.atan2(direct.y,direct.x))
        lp = math.sqrt(direct.x*direct.x+direct.y*direct.y)
        pitch = 90+r2d(math.atan2(direct.z,lp))
        profile.Placement = App.Placement(
            pos,
            App.Rotation(
                yaw,
                pitch,
                0
            ),
            utils.origin)
        profile.ViewObject.hide()

        noneRot = App.Rotation(App.Vector(0,0,1),0)

        sw = App.ActiveDocument.addObject('Part::Sweep')
        sw.Placement = App.Placement(offset,noneRot)
        sw.Sections = [profile]
        sw.Spine = (obj.Base,["Edge{}".format(i) for i in range(len(obj.Base.Shape.Edges),0,-1)])
        sw.Transition = "Round corner"
        sw.Solid = True
        sw.Frenet = True
        return sw

    def makeStairs(self,nRisers, h = 0, treadThickness = 0, riserHeight = 0, treadWidth = 0, nosing = 0):

        def vertF(p,n,wl,wr,h):
            """return a vertical Face
            
            p - midpoint of lower edge
            n - normal
            w - width
            h - height
            """

            up = utils.zAxis
            no = n.cross(up) # orthogonal

            f = [p - no*wl, p + no*wr, p + up*h + no*wr, p + up*h - no*wl]

            return f

        # helper mehod to create the faces
        def make_face(v,i):
            v = [v[j-1] for j in i]

            wire = Part.makePolygon(v+[v[0]])
            return Part.Face(wire)

        def makeSlab(vs):
            f1 = make_face(vs,[1,2,3,4])
            f2 = make_face(vs,[4,3,7,8])
            f3 = make_face(vs,[5,6,7,8])
            f4 = make_face(vs,[5,6,2,1])
            f5 = make_face(vs,[1,4,8,5])
            f6 = make_face(vs,[2,3,7,6])
            shell = Part.makeShell([f1,f2,f3,f4,f5,f6])
            solid = Part.makeSolid(shell)
            return solid

        def pz(v):
            return App.Vector(v.x,v.y,0)

        def pzn(v):
            return pz(v).normalize()

        if self.e is None:
            App.Console.PrintError("self.e empty in makeStairs\n")
            return

        tu = App.Units.parseQuantity
        defaultUnit = tu("1 mm") # so they say...

        e = self.e
        val = self.val

        # set up all default parameters 
        if h == 0:
            h = (e.valueAt(val[-1]).z - e.valueAt(val[0]).z) * defaultUnit

        riseHeight = (e.valueAt(val[1]).z - e.valueAt(val[0]).z)*defaultUnit

        riserHeight = riseHeight-treadThickness

        steps  = []   # this will be a list of shapes, one for each step (a union of the riser and the tread)
        pts = ({"p":e.valueAt(v),"t":self.flip*pzn(e.tangentAt(v))} for v in val)

#        print("pts = {}".format(list(pts)))

        for a,b in utils.pairwise(pts):
            # calculate the curvature (to limit width)
            ta = a['t']
            tb = b['t']
            alpha = ta.getAngle(tb)
            sense = ta.cross(ta-tb)

            pa = a['p']
            pb = b['p']
            l = pz(pa-pb).Length # horizontal distance between riser midpoints

            if alpha==0:
                maxw = float("inf")
            else:
                maxw = 0.499*abs(l/math.sin(alpha/2))

            # print("alpha,sense,maxw = {},{},{}".format(alpha,sense.z,maxw))

            if sense.z > 0:
                wl = treadWidth/2
                wr = min(treadWidth/2, maxw)
            else:
                wl = min(treadWidth/2, maxw)
                wr = treadWidth/2

            # the riser
            v1 = vertF(pa                  ,ta,wl,wr,riserHeight)
            v2 = vertF(pa+ta*treadThickness,ta,wl,wr,riserHeight)
            riser = makeSlab(v1+v2)

            # the tread
            #dz = riseHeight
            dz = pb.z-pa.z # should be identical to riseHeight
            offs = App.Vector(0,0,dz)-tb*nosing
            v1 = vertF(pa+offs,             ta,wl,wr,-treadThickness)
            v2 = vertF(pb+tb*treadThickness,tb,wl,wr,-treadThickness)
            tread = makeSlab(v1+v2)

            steps.extend([riser,tread])

        return functools.reduce(lambda x,y: x.fuse(y),steps)

    def onChanged(self, obj, prop):
        if prop == "Base" or prop == "housing":
            o = getattr(obj,prop)
            if o is not None:
                if hasattr(o,'Shape'):
                    if App.GuiUp:
                        o.ViewObject.hide()
                else:
                    App.Console.PrintWarning("Base and housing need to have Shape")
                    setattr(obj,prop,None) # only take objects with Shape

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

class ViewProviderStairs:
    def __init__(self,vobj):
        vobj.Proxy = self

        self._check_attr()
        dirname = os.path.dirname(__file__)
        self.icon_fn = os.path.join(dirname, "resources", "icons", "makeStairs.svg")

    def attach(self, vobj):
        """Called to attach viewprovider to object"""
        self.Object = vobj.Object

    def claimChildren(self):
        c = []
        if hasattr(self,"Object"):
            if hasattr(self.Object,"Base") and self.Object.Base is not None:
                c.append(self.Object.Base)
            if hasattr(self.Object,"Objects") and self.Object.Objects is not None:
                c.extend(self.Object.Objects)
            if hasattr(self.Object,"housing") and self.Object.housing is not None:
                c.append(self.Object.housing)
        return c

    def _check_attr(self):
        ''' Check for missing attributes. '''
        if not hasattr(self, "icon_fn"):
            setattr(self, "icon_fn", os.path.join(os.path.dirname(__file__), "resources", "icons", "makeStairs.svg"))

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

class makeStairs:
    def Activated(self):
        """Run the following code when the command is activated (button press)."""

        sel = FreeCADGui.Selection.getSelection() #" sel" contains the items selected

        if len(sel) == 0:
            App.Console.PrintError("stairs cannot be created from empty selection\n")
            return

        if not hasattr(sel[0],'Shape'):
            App.Console.PrintError("stairs can only be created from a shape\n")
            return

#        if not sel[0].isDerivedFrom("Part::Wire"):
#            App.Console.PrintError("stairs can only be created from a Part::Wire\n")
#            return

        obj = App.ActiveDocument.addObject("Part::FeaturePython" ,"Stairs" )
        genericStairs(obj)

        if App.GuiUp:
            ViewProviderStairs(obj.ViewObject)

        # base the stairs on the defining wire (usually a StairPath)
        obj.Base = sel[0]

        obj.touch()
        
        App.ActiveDocument.recompute()

    def IsActive(self):
        return len(FreeCADGui.Selection.getSelection())>0

    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""

        MenuText = QtCore.QT_TRANSLATE_NOOP("genericStairs","make stairs" )
        ToolTip  = QtCore.QT_TRANSLATE_NOOP("genericStairs","make stairs" )

        rel_path = "Mod/stairs2/Resources/icons/makeStairs.svg"
        path = App.getHomePath() + rel_path

        if not os.path.exists(path):
            path = App.getUserAppDataDir() + rel_path

        return {'Pixmap': path,'MenuText' : MenuText,'ToolTip' : ToolTip}

# The command must be "registered" with a unique name by calling its class.
FreeCADGui.addCommand('makeStairs', makeStairs())
