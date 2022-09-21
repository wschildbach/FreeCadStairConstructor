import itertools
import FreeCAD as App
import Part

# from importlib import reload
# import utils; reload(utils)

origin = App.Vector(0,0,0)
zAxis = App.Vector(0,0,1)

def ipol(x0,x,x1):
    """Interpolate between x0 and x1"""
    return (1-x) * x0 + x * x1

# from itertools import pairwise
def pairwise(iterable):
    import itertools
    """s -> (s0, s1), (s1, s2), (s2, s3), ..."""
   
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)  

class multiEdge:
    """A class that mimics "Edge" behavior, given an array of Edges (which should preferrably join).
    
    With this, one can use a parameter between 0 and the total length of the Edges, and call valueAt() and tangentAt().
    """
    
    def __init__(self, sh):

        self.Edges = Part.__sortEdges__(sh.Edges)

#        self.w = Part.Wire(edges)
#        if self.w.isClosed() then ERROR
        self.lens = [ e.Length for e in self.Edges ]

        self.cumLen = []
        self.FirstParameter = 0
        self.LastParameter = 0
        for l in self.lens:
            self.LastParameter += l
            self.cumLen.append(self.LastParameter)

        self.Length = self.LastParameter

    def mapTo(self,x):
        """map "global" parameter x into a tuple (edge,parameter on edge)"""

        if x < self.FirstParameter:
            x = self.FirstParameter
        elif x > self.LastParameter:
            x = self.LastParameter

        # search that edge that x maps into
        for i,l in enumerate(self.cumLen):
            if (l > x): break

        # this is the edge that x maps into
        theEdge = self.Edges[i]

        # map x into [0,1[
        x = 1.0+(x-self.cumLen[i])/self.lens[i]

        return (theEdge, ipol(theEdge.FirstParameter,x,theEdge.LastParameter))

    def valueAt(self, x):
        (e,xx) = self.mapTo(x)
        return e.valueAt(xx)

    def tangentAt(self, x):
        (e,xx) = self.mapTo(x)
        return e.tangentAt(xx)
