import os
import os.path as op
import logging

from pyrocko import guts, util
from pyrocko.guts import Dict, List, Tuple, Float, Unicode, Object, String, \
    StringPattern

from grond.plot.config import PlotFormat


guts_prefix = 'grond'

logger = logging.getLogger('grond.plot.collection')


class StringID(StringPattern):
    pattern = r'^[A-Za-z][A-Za-z0-9._]{0,64}$'


class PlotItem(Object):
    name = StringID.T()
    attributes = Dict.T(StringID.T(), List.T(String.T()))


class PlotGroup(Object):
    name = StringID.T()
    variant = StringID.T()
    description = Unicode.T(optional=True)
    formats = List.T(PlotFormat.T())
    size_cm = Tuple.T(2, Float.T())
    items = List.T(PlotItem.T())
    attributes = Dict.T(StringID.T(), List.T(String.T()))

    def filename_image(self, item, format):
        return '%s.%s.%s.%s' % (
            self.name,
            self.variant,
            item.name,
            format.extension)


class PlotCollection(Object):
    group_refs = List.T(Tuple.T(2, StringID.T()))


class PlotCollectionManager(object):

    def __init__(self, path):
        self._path = path
        self.load_collection()

    def load_collection(self):
        path = self.path_collection()
        if op.exists(path):
            self._collection = guts.load(filename=self.path_collection())
        else:
            self._collection = PlotCollection()

    def dump_collection(self):
        guts.dump(self._collection, filename=self.path_collection())

    def path_collection(self):
        return op.join(self._path, 'plot_collection.yaml')

    def path_image(self, group, item, format):
        return op.join(self._path, group.filename_image(item, format))

    def path_group(self, group_ref=None, group=None):
        if group_ref is not None:
            group_name, group_variant = group_ref
        else:
            group_name = group.name
            group_variant = group.variant

        return op.join(
            self._path, '%s.%s.%s' % (
                group_name, group_variant, 'plot_group.yaml'))

    def create_group_mpl(self, config, iter_item_figure, **kwargs):
        group = PlotGroup(
            formats=guts.clone(config.formats),
            size_cm=config.size_cm,
            name=config.name,
            variant=config.variant,
            **kwargs)

        path_group = self.path_group(group=group)
        if os.path.exists(path_group):
            self.remove_group_files(path_group)

        group_ref = (group.name, group.variant)
        if group_ref in self._collection.group_refs:
            self._collection.group_refs.remove(group_ref)

        self.dump_collection()

        for item, fig in iter_item_figure:
            group.items.append(item)
            for format in group.formats:
                path = self.path_image(group, item, format)
                util.ensuredirs(path)
                fig.savefig(
                    path,
                    format=format.name,
                    dpi=format.get_dpi(group.size_cm))

                logger.info('figure saved: %s' % path)

        util.ensuredirs(path_group)
        group.dump(filename=path_group)
        self._collection.group_refs.append(group_ref)
        self.dump_collection()

    def remove_group_files(self, path_group):
        group = guts.load(filename=path_group)
        for item in group.items:
            for format in group.formats:
                path = self.path_image(group, item, format)
                try:
                    os.unlink(path)
                except OSError:
                    pass

        os.unlink(path_group)


__all__ = [
    'StringID',
    'PlotItem',
    'PlotGroup',
    'PlotCollection',
    'PlotCollectionManager',
]