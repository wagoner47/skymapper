# Taken from http://matplotlib.org/examples/api/custom_projection_example.html
# and adapted to Albers Equal Area transform.
# CAUTION: This implementation does *not* work!
from __future__ import unicode_literals

import matplotlib
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from matplotlib.path import Path
from matplotlib.ticker import NullLocator, Formatter, FixedLocator
from matplotlib.transforms import Affine2D, BboxTransformTo, Transform
from matplotlib.projections import register_projection
import matplotlib.spines as mspines
import matplotlib.axis as maxis

import numpy as np

# This example projection class is rather long, but it is designed to
# illustrate many features, not all of which will be used every time.
# It is also common to factor out a lot of these methods into common
# code used by a number of projections with similar characteristics
# (see geo.py).


class AlbersEqualAreaAxes(Axes):
    """
    A custom class for the Albers Equal Area projection.

    https://en.wikipedia.org/wiki/Albers_projection
    """
    # The projection must specify a name.  This will be used be the
    # user to select the projection, i.e. ``subplot(111,
    # projection='aea')``.
    name = 'aea'

    def __init__(self, *args, **kwargs):
        self.dec_0 = kwargs.pop('dec_0', 0)
        self.dec_1 = kwargs.pop('dec_1', 0)
        self.dec_2 = kwargs.pop('dec_2', 60)
        self.ra_0 = kwargs.pop('ra_0', 0)

        Axes.__init__(self, *args, **kwargs)
#        self.set_aspect(00.75, adjustable='box', anchor='C')
        self.cla()

    def _init_axis(self):
        self.xaxis = maxis.XAxis(self)
        self.yaxis = maxis.YAxis(self)
        # Do not register xaxis or yaxis with spines -- as done in
        # Axes._init_axis() -- until HammerAxes.xaxis.cla() works.
        #self.spines['hammer'].register_axis(self.yaxis)
        self._update_transScale()

    def cla(self):
        """
        Override to set up some reasonable defaults.
        """
        # Don't forget to call the base class
        Axes.cla(self)

        # Set up a default grid spacing
        self.set_longitude_grid(30)
        self.set_latitude_grid(15)
        self.set_longitude_grid_ends(75)

        # Turn off minor ticking altogether
        self.xaxis.set_minor_locator(NullLocator())
        self.yaxis.set_minor_locator(NullLocator())

        # Do not display ticks -- we only want gridlines and text
        self.xaxis.set_ticks_position('none')
        self.yaxis.set_ticks_position('none')

        # The limits on this projection are fixed -- they are not to
        # be changed by the user.  This makes the math in the
        # transformation itself easier, and since this is a toy
        # example, the easier, the better.
        Axes.set_xlim(self, 0, 360)
        Axes.set_ylim(self, -90, 90)

    def _set_lim_and_transforms(self):
        """
        This is called once when the plot is created to set up all the
        transforms for the data, text and grids.
        """
        # There are three important coordinate spaces going on here:
        #
        #    1. Data space: The space of the data itself
        #
        #    2. Axes space: The unit rectangle (0, 0) to (1, 1)
        #       covering the entire plot area.
        #
        #    3. Display space: The coordinates of the resulting image,
        #       often in pixels or dpi/inch.

        # This function makes heavy use of the Transform classes in
        # ``lib/matplotlib/transforms.py.`` For more information, see
        # the inline documentation there.

        # The goal of the first two transformations is to get from the
        # data space (in this case longitude and latitude) to axes
        # space.  It is separated into a non-affine and affine part so
        # that the non-affine part does not have to be recomputed when
        # a simple affine change to the figure has been made (such as
        # resizing the window or changing the dpi).

        # 1) The core transformation from data space into
        # rectilinear space defined in the HammerTransform class.
        self.transProjection = self.AlbersEqualAreaTransform(ra_0=self.ra_0, 
                        dec_0=self.dec_0, dec_1=self.dec_1, dec_2=self.dec_2)

        # 2) The above has an output range that is not in the unit
        # rectangle, so scale and translate it so it fits correctly
        # within the axes.  The peculiar calculations of xscale and
        # yscale are specific to a Aitoff-Hammer projection, so don't
        # worry about them too much.
        xscale = self.transProjection.xscale
        yscale = self.transProjection.yscale

        self.transAffine = Affine2D() \
            .scale(0.5 / xscale, 0.5 / yscale) \
            .translate(0.5, 0.5)

        # 3) This is the transformation from axes space to display
        # space.
        self.transAxes = BboxTransformTo(self.bbox)

        # Now put these 3 transforms together -- from data all the way
        # to display coordinates.  Using the '+' operator, these
        # transforms will be applied "in order".  The transforms are
        # automatically simplified, if possible, by the underlying
        # transformation framework.
        self.transData = \
            self.transProjection + \
            self.transAffine + \
            self.transAxes

        # The main data transformation is set up.  Now deal with
        # gridlines and tick labels.

        # Longitude gridlines and ticklabels.  The input to these
        # transforms are in display space in x and axes space in y.
        # Therefore, the input values will be in range (-xmin, 0),
        # (xmax, 1).  The goal of these transforms is to go from that
        # space to display space.  The tick labels will be offset 4
        # pixels from the equator.
        self._xaxis_pretransform = \
            Affine2D() \
            .scale(1.0, 180) \
            .translate(0.0, -90)
        self._xaxis_transform = \
            self._xaxis_pretransform + \
            self.transData
        self._xaxis_text1_transform = \
            Affine2D().scale(1.0, 0.0) + \
            self.transData + \
            Affine2D().translate(0.0, 0.0)
        self._xaxis_text2_transform = \
            Affine2D().scale(1.0, 0.0) + \
            self.transData + \
            Affine2D().translate(0.0, 0.0)

        # Now set up the transforms for the latitude ticks.  The input to
        # these transforms are in axes space in x and display space in
        # y.  Therefore, the input values will be in range (0, -ymin),
        # (1, ymax).  The goal of these transforms is to go from that
        # space to display space.  The tick labels will be offset 4
        # pixels from the edge of the axes ellipse.
        yaxis_stretch = Affine2D().scale(360, 1.0).translate(0.0, 0.0)
        yaxis_space = Affine2D().scale(1.0, 1.0)
        self._yaxis_transform = \
            yaxis_stretch + \
            self.transData
        yaxis_text_base = \
            yaxis_stretch + \
            self.transProjection + \
            (yaxis_space +
             self.transAffine +
             self.transAxes)
        self._yaxis_text1_transform = \
            yaxis_text_base + \
            Affine2D().translate(-8.0, 0.0)
        self._yaxis_text2_transform = \
            yaxis_text_base + \
            Affine2D().translate(8.0, 0.0)

    def get_xaxis_transform(self, which='grid'):
        """
        Override this method to provide a transformation for the
        x-axis grid and ticks.
        """
        assert which in ['tick1', 'tick2', 'grid']
        return self._xaxis_transform

    def get_xaxis_text1_transform(self, pixelPad):
        """
        Override this method to provide a transformation for the
        x-axis tick labels.

        Returns a tuple of the form (transform, valign, halign)
        """
        return self._xaxis_text1_transform, 'bottom', 'center'

    def get_xaxis_text2_transform(self, pixelPad):
        """
        Override this method to provide a transformation for the
        secondary x-axis tick labels.

        Returns a tuple of the form (transform, valign, halign)
        """
        return self._xaxis_text2_transform, 'top', 'center'

    def get_yaxis_transform(self, which='grid'):
        """
        Override this method to provide a transformation for the
        y-axis grid and ticks.
        """
        assert which in ['tick1', 'tick2', 'grid']
        return self._yaxis_transform

    def get_yaxis_text1_transform(self, pixelPad):
        """
        Override this method to provide a transformation for the
        y-axis tick labels.

        Returns a tuple of the form (transform, valign, halign)
        """
        return self._yaxis_text1_transform, 'center', 'center'

    def get_yaxis_text2_transform(self, pixelPad):
        """
        Override this method to provide a transformation for the
        secondary y-axis tick labels.

        Returns a tuple of the form (transform, valign, halign)
        """
        return self._yaxis_text2_transform, 'center', 'center'

    def _gen_axes_patch(self):
        """
        Override this method to define the shape that is used for the
        background of the plot.  It should be a subclass of Patch.

        In this case, it is a Circle (that may be warped by the axes
        transform into an ellipse).  Any data and gridlines will be
        clipped to this shape.
        """
        return Rectangle((0, 0), 1, 1)

    def _gen_axes_spines(self):
        d = {
            'left': mspines.Spine.linear_spine(self, spine_type='left'), 
            'right': mspines.Spine.linear_spine(self, spine_type='right'),
            'top': mspines.Spine.linear_spine(self, spine_type='top'),
            'bottom': mspines.Spine.linear_spine(self, spine_type='bottom'),
        }
        d['left'].set_position(('axes', 0))
        d['right'].set_position(('axes', 1))
        d['top'].set_position(('axes', 0))
        d['bottom'].set_position(('axes', 1))
        return d
    # Prevent the user from applying scales to one or both of the
    # axes.  In this particular case, scaling the axes wouldn't make
    # sense, so we don't allow it.
    def set_xscale(self, *args, **kwargs):
        if args[0] != 'linear':
            raise NotImplementedError
        Axes.set_xscale(self, *args, **kwargs)

    def set_yscale(self, *args, **kwargs):
        if args[0] != 'linear':
            raise NotImplementedError
        Axes.set_yscale(self, *args, **kwargs)

    # Prevent the user from changing the axes limits.  In our case, we
    # want to display the whole sphere all the time, so we override
    # set_xlim and set_ylim to ignore any input.  This also applies to
    # interactive panning and zooming in the GUI interfaces.
    def set_xlim(self, *args, **kwargs):
        Axes.set_xlim(self, 0, 360)
        Axes.set_ylim(self, -90, 90)
    set_ylim = set_xlim

    def format_coord(self, lon, lat):
        """
        Override this method to change how the values are displayed in
        the status bar.

        In this case, we want them to be displayed in degrees N/S/E/W.
        """
        lon = lon
        lat = lat
        if lat >= 0.0:
            ns = 'N'
        else:
            ns = 'S'
        if lon >= 0.0:
            ew = 'E'
        else:
            ew = 'W'
        # \u00b0 : degree symbol
        return '%f\u00b0%s, %f\u00b0%s' % (abs(lat), ns, abs(lon), ew)

    class DegreeFormatter(Formatter):
        """
        This is a custom formatter that converts the native unit of
        radians into (truncated) degrees and adds a degree symbol.
        """

        def __init__(self, round_to=1.0):
            self._round_to = round_to

        def __call__(self, x, pos=None):
            degrees = round(x / self._round_to) * self._round_to
            # \u00b0 : degree symbol
            return "%d\u00b0" % degrees

    def set_longitude_grid(self, degrees):
        """
        Set the number of degrees between each longitude grid.

        This is an example method that is specific to this projection
        class -- it provides a more convenient interface to set the
        ticking than set_xticks would.
        """
        # Set up a FixedLocator at each of the points, evenly spaced
        # by degrees.
        number = (360.0 / degrees) + 1
        self.xaxis.set_major_locator(
            FixedLocator(
                np.linspace(0, 360, number, True)[1:-1]))
        # Set the formatter to display the tick labels in degrees,
        # rather than radians.
        self.xaxis.set_major_formatter(self.DegreeFormatter(degrees))

    def set_latitude_grid(self, degrees):
        """
        Set the number of degrees between each longitude grid.

        This is an example method that is specific to this projection
        class -- it provides a more convenient interface than
        set_yticks would.
        """
        # Set up a FixedLocator at each of the points, evenly spaced
        # by degrees.
        number = (180.0 / degrees) + 1
        self.yaxis.set_major_locator(
            FixedLocator(
                np.linspace(-90, 90, number, True)[1:-1]))
        # Set the formatter to display the tick labels in degrees,
        # rather than radians.
        self.yaxis.set_major_formatter(self.DegreeFormatter(degrees))

    def set_longitude_grid_ends(self, degrees):
        """
        Set the latitude(s) at which to stop drawing the longitude grids.

        Often, in geographic projections, you wouldn't want to draw
        longitude gridlines near the poles.  This allows the user to
        specify the degree at which to stop drawing longitude grids.

        This is an example method that is specific to this projection
        class -- it provides an interface to something that has no
        analogy in the base Axes class.
        """
        longitude_cap = degrees
        # Change the xaxis gridlines transform so that it draws from
        # -degrees to degrees, rather than -pi to pi.
        self._xaxis_pretransform \
            .clear() \
            .scale(1.0, longitude_cap * 2.0) \
            .translate(0.0, -longitude_cap)

#    def get_data_ratio(self):
#        """
#        Return the aspect ratio of the data itself.
#
#        This method should be overridden by any Axes that have a
#        fixed data ratio.
#        """
#        return 1.0

    # Interactive panning and zooming is not supported with this projection,
    # so we override all of the following methods to disable it.

    def can_zoom(self):
        """
        Return True if this axes support the zoom box
        """
        return False

    def start_pan(self, x, y, button):
        pass

    def end_pan(self):
        pass

    def drag_pan(self, button, key, x, y):
        pass

    # Now, the transforms themselves.

    class AlbersEqualAreaTransform(Transform):
        """
        The base Hammer transform.
        """
        input_dims = 2
        output_dims = 2
        is_separable = False

        def __init__(self, ra_0=0, dec_0=0, dec_1=0, dec_2=60, **kwargs):
            Transform.__init__(self, **kwargs)
            self.dec_0 = dec_0
            self.dec_1 = dec_1
            self.dec_2 = dec_2
            self.ra_0 = ra_0
            self.deg2rad = np.pi/180

            self.n = (np.sin(dec_1 * self.deg2rad) + np.sin(dec_2 * self.deg2rad)) / 2
            self.C = np.cos(dec_1 * self.deg2rad)**2 + 2 * self.n * np.sin(dec_1 * self.deg2rad)
            self.rho_0 = self.__rho__(dec_0)
            edges = self.transform_non_affine(
                np.array([[ra_0 - 180, -90], [ra_0 + 180, -90], [ra_0, -90]]))

            self.x_0 = edges[0][0]
            self.x_1 = edges[1][0]
            self.xscale = np.abs(self.x_0 - self.x_1)
            self.y_0 = edges[2][1]
            self.y_1 = edges[0][1]
            self.yscale = np.abs(self.y_0 - self.y_1)

        def __rho__(self, dec):
            return np.sqrt(self.C - 2 * self.n * np.sin(dec * self.deg2rad)) / self.n

        def transform_non_affine(self, ll):
            """
            Override the transform_non_affine method to implement the custom
            transform.

            The input and output are Nx2 numpy arrays.
            """
            ra = ll[:,0]
            dec = ll[:,1]

            ra_ = np.array([ra - self.ra_0])# * -1 # inverse for RA
            # check that ra_ is between -180 and 180 deg
            ra_[ra_ < -180 ] += 360
            ra_[ra_ > 180 ] -= 360

            # FIXME: problem with the slices sphere: outer parallel needs to be dubplicated at the expense of the central one
            theta = self.n * ra_[0]
            rho = self.__rho__(dec)
            rt = np.array([
                rho*np.sin(theta * self.deg2rad), 
                 self.rho_0 - rho*np.cos(theta * self.deg2rad)]).T
            if np.isnan(rt).any(): raise ValueError('abc')
            return rt 

        # This is where things get interesting.  With this projection,
        # straight lines in data space become curves in display space.
        # This is done by interpolating new values between the input
        # values of the data.  Since ``transform`` must not return a
        # differently-sized array, any transform that requires
        # changing the length of the data array must happen within
        # ``transform_path``.
        def transform_path_non_affine(self, path):
            isteps = path._interpolation_steps * 2
            while True:
                ipath = path.interpolated(isteps)
                tiv = self.transform(ipath.vertices)
                itv = Path(self.transform(path.vertices)).interpolated(isteps).vertices
                if np.mean(np.abs(tiv - itv)) < 0.1: 
#                    print 'isteps', isteps
                    break
                if isteps > 80: 
#                    print 'diff', np.mean(np.abs(tiv - itv)) 
                    break
                isteps = isteps * 2 
            #return Path(self.transform(ipath.vertices), ipath.codes)
            codes = []
            vertices = []
            vlast = None
            for v, c in ipath.iter_segments(simplify=False, curves=False):
                skip = False
                if vlast is not None: 
#                    print np.abs(v[0] - vlast[0])
                    d0 = (v[0] - (self.ra_0 + 180)) 
                    d1 = (vlast[0] - (self.ra_0 + 180))
                    if (d0 * d1 <= 0)and not (d0 == 0 and d1 == 0):
                        skip = True
                if not skip:
                    codes.append(c)
                    vertices.append(v)
                else:
                    codes.append(1)
                    vertices.append(v)
                vlast = v

            return Path(self.transform(vertices), codes)

        transform_path_non_affine.__doc__ = \
            Transform.transform_path_non_affine.__doc__

        if matplotlib.__version__ < '1.2':
            # Note: For compatibility with matplotlib v1.1 and older, you'll
            # need to explicitly implement a ``transform`` method as well.
            # Otherwise a ``NotImplementedError`` will be raised. This isn't
            # necessary for v1.2 and newer, however.
            transform = transform_non_affine

            # Similarly, we need to explicitly override ``transform_path`` if
            # compatibility with older matplotlib versions is needed. With v1.2
            # and newer, only overriding the ``transform_path_non_affine``
            # method is sufficient.
            transform_path = transform_path_non_affine
            transform_path.__doc__ = Transform.transform_path.__doc__

        def inverted(self):
            return AlbersEqualAreaAxes.InvertedAlbersEqualAreaTransform(ra_0=self.ra_0, dec_0=self.dec_0, dec_1=self.dec_1, dec_2=self.dec_2)
        inverted.__doc__ = Transform.inverted.__doc__

    class InvertedAlbersEqualAreaTransform(Transform):
        input_dims = 2
        output_dims = 2
        is_separable = False

        def __init__(self, ra_0=0, dec_0=0, dec_1=-30, dec_2=30, **kwargs):
            Transform.__init__(self, **kwargs)
            self.dec_0 = dec_0
            self.dec_1 = dec_1
            self.ra_0 = ra_0
            self.deg2rad = np.pi/180

            self.n = (np.sin(dec_1 * self.deg2rad) + np.sin(dec_2 * self.deg2rad)) / 2
            self.C = np.cos(dec_1 * self.deg2rad)**2 + 2 * self.n * np.sin(dec_1 * self.deg2rad)
            self.rho_0 = self.__rho__(dec_0)

        def __rho__(self, dec):
            return np.sqrt(self.C - 2 * self.n * np.sin(dec * self.deg2rad)) / self.n


        def transform_non_affine(self, xy):
            x = xy[:,0]
            y = xy[:,1]

            rho = np.sqrt(x**2 + (self.rho_0 - y)**2)
            theta = np.arctan(x/(self.rho_0 - y)) / self.deg2rad
            return np.array([self.ra_0 + theta/self.n, 
                np.arcsin((self.C - (rho * self.n)**2)/(2*self.n)) / self.deg2rad]).T

            transform_non_affine.__doc__ = Transform.transform_non_affine.__doc__

        # As before, we need to implement the "transform" method for
        # compatibility with matplotlib v1.1 and older.
        if matplotlib.__version__ < '1.2':
            transform = transform_non_affine

        def inverted(self):
            # The inverse of the inverse is the original transform... ;)
            return AlbersEqualAreaAxes.AlbersEqualAreaTransform(ra_0=self.ra_0, dec_0=self.dec_0, dec_1=self.dec_1, dec_2=self.dec_2)
        inverted.__doc__ = Transform.inverted.__doc__

# Now register the projection with matplotlib so the user can select
# it.
register_projection(AlbersEqualAreaAxes)

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    # Now make a simple example using the custom projection.
    plt.subplot(111, projection="aea")
    p = plt.plot([-1, 1, 1], [-1, -1, 1], "o-")
    plt.grid(True)

    plt.show()
