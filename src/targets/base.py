import copy

import numpy as num

from pyrocko import gf
from pyrocko.guts_array import Array
from pyrocko.guts import Object, Float, Dict

from grond.analysers.base import AnalyserResult


guts_prefix = 'grond'


class TargetGroup(Object):
    normalisation_family = gf.StringID.T(
        optional=True,
        help='Group with common misfit normalisation')
    path = gf.StringID.T(
        optional=True,
        help='Targets.id will be prefixed with this path')
    weight = Float.T(
        default=1.0,
        help='Additional manual weight of the target group')
    interpolation = gf.InterpolationMethod.T(
        default='nearest_neighbor',
        help='Interpolation from pre-calculated GF store.')
    store_id = gf.StringID.T(
        optional=True,
        help='ID of the Green\'s function store for this TargetGroup.')

    def get_targets(self, ds, event, default_path):
        raise NotImplementedError()


class MisfitResult(Object):
    misfits = Array.T(
        shape=(None, 2),
        dtype=num.float)


class MisfitConfig(Object):
    pass


class MisfitTarget(Object):

    manual_weight = Float.T(
        default=1.0,
        help='Relative weight of this target')
    analyser_results = Dict.T(
        gf.StringID.T(),
        AnalyserResult.T(),
        help='Analysers put their results here')
    normalisation_family = gf.StringID.T(
        optional=True,
        help='Normalisation family of this misfit target')
    path = gf.StringID.T(
        help='A path identifier used for plotting')
    misfit_config = MisfitConfig.T(
        default=MisfitConfig.D(),
        help='Misfit configuration')

    def __init__(self, **kwargs):
        Object.__init__(self, **kwargs)
        self.parameters = []

        self._ds = None
        self._result_mode = 'sparse'

        self._target_parameters = None
        self._target_ranges = None

    @classmethod
    def get_plot_classes(cls):
        return []

    def set_dataset(self, ds):
        self._ds = ds

    def get_dataset(self):
        return self._ds

    @property
    def nmisfits(self):
        return 1

    @property
    def nparameters(self):
        if self._target_parameters is None:
            return 0
        return len(self._target_parameters)

    @property
    def target_parameters(self):
        if self._target_parameters is None:
            self._target_parameters = copy.deepcopy(self.parameters)
            for p in self._target_parameters:
                p.set_groups([self.string_id()])
        return self._target_parameters

    @property
    def target_ranges(self):
        return {}

    def set_parameter_values(self, model):
        for i, p in enumerate(self.parameters):
            self.parameter_values[p.name_nogroups] = model[i]

    def set_result_mode(self, result_mode):
        self._result_mode = result_mode

    def post_process(self, engine, source, statics):
        raise NotImplementedError()

    def get_combined_weight(self):
        return num.ones(1, dtype=num.float)

    def prepare_modelling(self, engine, source, targets):
        return []

    def finalize_modelling(
            self, engine, source, modelling_targets, modelling_results):

        raise NotImplemented('must be overloaded in subclass')


__all__ = '''
    TargetGroup
    MisfitTarget
    MisfitResult
'''.split()
