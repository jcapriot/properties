import numpy as np
import os
import properties
import unittest


class SomeOptions(properties.PropertyClass):
    color = properties.Color("My color")


class MySurface(properties.PropertyClass):
    opts = properties.Pointer("My options",
                              ptype=SomeOptions, expose=['color'])


class MyInitSurface(MySurface):
    def __init__(self, opts, **kwargs):
        super(MyInitSurface, self).__init__(**kwargs)
        self.opts = opts


class MyShapeAutoTrue(properties.PropertyClass):
    surf = properties.Pointer("Init sfc", ptype=MyInitSurface)


class MyShapeAutoFalse(properties.PropertyClass):
    surf = properties.Pointer("Init sfc",
                              ptype=MyInitSurface, auto_create=False)


class MyShape(properties.PropertyClass):
    surf = properties.Pointer("The surface",
                              ptype=MySurface, required=True)
    sub_surfs = properties.Pointer("The sub-surface",
                                   ptype=MySurface, repeated=True)
    opts = properties.Pointer("My other options",
                              ptype=SomeOptions)


class OneOfMany(properties.PropertyClass):
    prop = properties.Pointer("Some Prop",
                              ptype=[SomeOptions, MySurface, MyShape])


class ManyOfMany(properties.PropertyClass):
    prop = properties.Pointer("Some Prop",
                              ptype=[MySurface, MyShape], repeated=True)


class TestBasic(unittest.TestCase):

    def test_resolve(self):
        class MyShapeStrPt(properties.PropertyClass):
            surf = properties.Pointer("The surface",
                                      ptype='MySurface', required=True)
            sub_surfs = properties.Pointer("The sub-surface",
                                           ptype='MySurface', repeated=True)
            opts = properties.Pointer("My other options",
                                      ptype=SomeOptions, auto_create=True)

        shp = MyShapeStrPt()
        sfc = MySurface()
        self.assertRaises(AttributeError, lambda: setattr(shp, 'surf', sfc))
        properties.Pointer.resolve()
        setattr(shp, 'surf', sfc)
        assert shp.surf is sfc
        assert shp.surf is shp.surf

    def test_expose(self):
        opts = SomeOptions()
        sfc = MySurface(opts=opts)
        assert sfc.color is sfc.opts.color
        assert opts.color is sfc.color

    def test_auto_create(self):
        shp = MyShape()
        sfc = MySurface()
        assert isinstance(shp.surf, MySurface)
        shp.surf = sfc
        assert getattr(shp, 'opts', None) is not None
        assert isinstance(shp.opts, SomeOptions)

        shp_t = MyShapeAutoTrue()
        self.assertRaises(AttributeError, lambda: shp_t.surf)

        shp_f = MyShapeAutoFalse()
        assert shp_f.surf is None

    def test_parent_child(self):
        class MyPossiblyEmptyShape(properties.PropertyClass):
            sub_surfs = properties.Pointer("The sub-surface",
                                           ptype='MySurfaceWithParent',
                                           repeated=True)
            opts = properties.Pointer("My other options",
                                      ptype='SomeOptions', auto_create=True)

        class MySurfaceWithParent(properties.PropertyClass):
            parent = properties.Pointer("Parent Shape",
                                        ptype='MyPossiblyEmptyShape',
                                        required=True)

            def __init__(self, parent=None, **kwargs):
                if parent is None:
                    raise TypeError('You must provide parent')
                super(MySurfaceWithParent, self).__init__(**kwargs)
                self.parent = parent
                self.parent.sub_surfs += [self]

        properties.Pointer.resolve()
        P = MyPossiblyEmptyShape()
        self.assertRaises(TypeError, lambda: MySurfaceWithParent())
        S0 = MySurfaceWithParent(P)
        S1 = MySurfaceWithParent(P)
        S2 = MySurfaceWithParent(P)

        assert P.sub_surfs == P.sub_surfs
        assert len(P.sub_surfs) == 3
        assert P.sub_surfs[0] is P.sub_surfs[0]
        assert P.sub_surfs[0] is S0
        assert P.sub_surfs[1] is S1
        assert P.sub_surfs[2] is S2

        P.validate()

    def test_list_ptype(self):

        class SomeStringPtypes(properties.PropertyClass):
            prop = properties.Pointer("Some Prop", ptype=[SomeOptions, 'MySurface', 'MyShape'])

        properties.Pointer.resolve()

        OOM = OneOfMany()
        MOM = ManyOfMany()
        SSP = SomeStringPtypes()

        shp = MyShape()
        sfc = MySurface()
        opt = SomeOptions()

        OOM.prop = shp
        OOM.prop = opt
        self.assertRaises(TypeError,
                          lambda: setattr(OOM, 'prop', MOM))

        MOM.prop = shp
        MOM.prop = [shp, sfc]
        self.assertRaises(TypeError,
                          lambda: setattr(MOM, 'prop', [shp, sfc, opt]))

        SSP.prop = shp
        SSP.prop = opt
        self.assertRaises(TypeError,
                          lambda: setattr(SSP, 'prop', MOM))

    def test_dirty(self):
        class MyShapeZero(properties.PropertyClass):
            surf = properties.Pointer("The surface", ptype=MySurface, repeated=True)
            opts = properties.Pointer("Shape options", ptype=SomeOptions)
            shp1 = properties.Pointer("Shape 1", ptype='MyShapeOne')

        class MyShapeOne(properties.PropertyClass):
            surf = properties.Pointer("The surface", ptype=MySurface, repeated=True)
            opts = properties.Pointer("Shape options", ptype=SomeOptions)
            shp2 = properties.Pointer("Shape 2", ptype='MyShapeTwo')

        class MyShapeTwo(properties.PropertyClass):
            surf = properties.Pointer("The surface", ptype=MySurface, repeated=True)
            opts = properties.Pointer("Shape options", ptype=SomeOptions)
            shp0 = properties.Pointer("Shape 0", ptype='MyShapeZero')

        properties.Pointer.resolve()

        S0 = MyShapeZero()
        S1 = MyShapeOne()
        S2 = MyShapeTwo()

        O0 = SomeOptions()
        O1 = SomeOptions()
        O2 = SomeOptions()

        sA = MySurface()
        sB = MySurface()
        sC = MySurface()

        OA = SomeOptions()
        OB = SomeOptions()
        OC = SomeOptions()

        assert len(O0._dirty) == 0#1
        # assert O0._dirty.issuperset(['color'])

        O0._mark_clean()
        assert len(O0._dirty) == 0

        S0.opts = O0
        assert len(O0._dirty) == 0
        assert len(S0._dirty) == 1
        O0.color = 'red'
        assert len(S0._dirty) == 1
        assert len(O0._dirty) == 1
        S0._mark_clean()
        assert len(S0._dirty) == 0
        assert len(O0._dirty) == 0

        S1.opts = O1
        assert len(S1._dirty) == 1
        assert len(O1._dirty) == 0
        O1.color = 'red'
        S1._mark_clean(False)
        assert len(S1._dirty) == 1
        assert len(O1._dirty) == 1

        S2.opts = O2
        S0.shp1 = S1
        S1.shp2 = S2
        S2.shp0 = S0

        assert len(S2._dirty) == 2
        assert len(S1._dirty) == 2
        assert len(S0._dirty) == 1

        sA.opts = OA
        sB.opts = OB
        sC.opts = OC

        S0.surf = [sA, sB, sC]
        S1.surf = [sA, sB, sC]
        S2.surf = [sA, sB, sC]

        O0.color = 'blue'
        assert len(S0._dirty) == 3
        assert len(S1._dirty) == 3
        assert len(S2._dirty) == 3

        S0._mark_clean()
        assert len(S0._dirty) == 0
        assert len(S1._dirty) == 0
        assert len(S2._dirty) == 0




if __name__ == '__main__':
    unittest.main()
