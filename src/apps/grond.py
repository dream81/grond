#!/usr/bin/env python

from __future__ import print_function, absolute_import

import sys
import os.path as op
import logging
from optparse import OptionParser, OptionValueError

from pyrocko import util, marker

import grond

logger = logging.getLogger('grond.main')
km = 1e3


def d2u(d):
    if isinstance(d, dict):
        return dict((k.replace('-', '_'), v) for (k, v) in d.items())
    else:
        return d.replace('-', '_')


subcommand_descriptions = {
    'init': 'initialise new project structure or print configuration',
    'scenario': 'create a forward-modelled scenario project',
    'events': 'print available event names for given configuration',
    'check': 'check data and configuration',
    'go': 'run Grond optimisation',
    'forward': 'run forward modelling',
    'harvest': 'manually run harvesting',
    'plot': 'plot optimisation result',
    'movie': 'visualize optimiser evolution',
    'export': 'export results',
    'report': 'create result report',
    'diff': 'compare two configs or other normalized Grond YAML files',
    'qc-polarization': 'check sensor orientations with polarization analysis',
    'upgrade-config': 'upgrade config file to the latest version of Grond',
    'version': 'print version number of Grond and its main dependencies',
}

subcommand_usages = {
    'init': 'init [options] <project_dir>',
    'scenario': 'scenario [options] <project_dir>',
    'events': 'events <configfile>',
    'check': 'check <configfile> <eventnames> ... [options]',
    'go': 'go <configfile> <eventnames> ... [options]',
    'forward': (
        'forward <rundir> [options]',
        'forward <configfile> <eventnames> ... [options]'),
    'harvest': 'harvest <rundir> [options]',
    'plot': (
        'plot <plotnames> ( <rundir> | <configfile> <eventname> ) [options]',
        'plot all ( <rundir> | <configfile> <eventname> ) [options]',
        'plot <plotconfigfile> ( <rundir> | <configfile> <eventname> ) [options]',  # noqa
        'plot list ( <rundir> | <configfile> <eventname> ) [options]',
        'plot config ( <rundir> | <configfile> <eventname> ) [options]'),
    'movie': 'movie <rundir> <xpar> <ypar> <filetemplate> [options]',
    'export': 'export (best|mean|ensemble|stats) <rundirs> ... [options]',
    'report': (
        'report <rundir> ... [options]',
        'report <configfile> <eventnames> ...'),
    'diff': 'diff <left_path> <right_path>',
    'qc-polarization': 'qc-polarization <configfile> <eventname> '
                       '<target_group_path> [options]',
    'upgrade-config': 'upgrade-config <configfile>',
    'version': 'version',
}

subcommands = subcommand_descriptions.keys()

program_name = 'grond'

usage_tdata = d2u(subcommand_descriptions)
usage_tdata['program_name'] = program_name
usage_tdata['version_number'] = grond.__version__


usage = '''%(program_name)s <subcommand> [options] [--] <arguments> ...

Grond is a probabilistic earthquake source inversion framework.

This is Grond version %(version_number)s.

Subcommands:

    scenario        %(scenario)s
    init            %(init)s
    events          %(events)s
    check           %(check)s
    go              %(go)s
    forward         %(forward)s
    harvest         %(harvest)s
    plot            %(plot)s
    movie           %(movie)s
    export          %(export)s
    report          %(report)s
    diff            %(diff)s
    qc-polarization %(qc_polarization)s
    upgrade-config  %(upgrade_config)s
    version         %(version)s

To get further help and a list of available options for any subcommand run:

    %(program_name)s <subcommand> --help

What do you want to bust today?!
''' % usage_tdata


class CLIHints(object):
    init = '''
We created a folder structure in {project_dir}.
Check out the YAML configuration in {config} and start the optimisation by:

    grond go {config}
'''
    scenario = '''
To start the scenario's optimisation, change to folder

    cd {project_dir}

Check out the YAML configuration in {config} and start the optimisation by:

    grond go {config}
'''
    report = '''
To open the reports in your web browser, run

    grond report -s --open {config}
'''
    check = '''
To start the optimisation, run

    grond go {config}
'''
    go = '''
To look at the results, run

    grond report -so {rundir}
'''

    def __new__(cls, command, **kwargs):
        return 'Hint:\n' +\
            getattr(cls, command).format(**kwargs)


def main(args=None):
    if not args:
        args = sys.argv

    args = list(sys.argv)
    if len(args) < 2:
        sys.exit('Usage: %s' % usage)

    args.pop(0)
    command = args.pop(0)

    if command in subcommands:
        globals()['command_' + d2u(command)](args)

    elif command in ('--help', '-h', 'help'):
        if command == 'help' and args:
            acommand = args[0]
            if acommand in subcommands:
                globals()['command_' + acommand](['--help'])

        sys.exit('Usage: %s' % usage)

    else:
        die('no such subcommand: %s' % command)


def add_common_options(parser):
    parser.add_option(
        '--loglevel',
        action='store',
        dest='loglevel',
        type='choice',
        choices=('critical', 'error', 'warning', 'info', 'debug'),
        default='info',
        help='set logger level to '
             '"critical", "error", "warning", "info", or "debug". '
             'Default is "%default".')

    parser.add_option(
        '--docs',
        dest='rst_docs',
        action='store_true')


def print_docs(command, parser):

    from optparse import IndentedHelpFormatter

    class DocsFormatter(IndentedHelpFormatter):

        def format_heading(self, heading):
            return '%s\n%s\n\n' % (heading, '.'*len(heading))

        def format_usage(self, usage):
            lines = usage.splitlines()
            return self.format_heading('Usage') + \
                '.. code-block:: none\n\n%s' % '\n'.join(
                    '    '+line.strip() for line in lines)

        def format_option(self, option):
            if not option.help:
                return ''

            result = []
            opts = self.option_strings[option]
            result.append('\n.. describe:: %s\n\n' % opts)

            help_text = self.expand_default(option)
            result.append('    %s\n\n' % help_text)

            return ''.join(result)

    parser.formatter = DocsFormatter()
    parser.formatter.set_parser(parser)

    def format_help(parser):
        formatter = parser.formatter
        result = []

        result.append(parser.format_description(formatter) + "\n")

        if parser.usage:
            result.append(parser.get_usage() + "\n")

        result.append('\n')

        result.append(parser.format_option_help(formatter))

        result.append('\n')

        result.append(parser.format_epilog(formatter))
        return "".join(result)

    print(command)
    print('-' * len(command))
    print()
    print('.. program:: %s' % program_name)
    print()
    print('.. option:: %s' % command)
    print()
    print(format_help(parser))


def process_common_options(command, parser, options):
    util.setup_logging(program_name, options.loglevel)
    if options.rst_docs:
        print_docs(command, parser)
        exit(0)


def cl_parse(command, args, setup=None, details=None):
    usage = subcommand_usages[command]
    descr = subcommand_descriptions[command]

    if isinstance(usage, str):
        usage = [usage]

    susage = '%s %s' % (program_name, usage[0])
    for s in usage[1:]:
        susage += '\n%s%s %s' % (' '*7, program_name, s)

    description = descr[0].upper() + descr[1:] + '.'

    if details:
        description = description + '\n\n%s' % details

    parser = OptionParser(usage=susage, description=description)

    if setup:
        setup(parser)

    add_common_options(parser)
    (options, args) = parser.parse_args(args)
    process_common_options(command, parser, options)
    return parser, options, args


def die(message, err=''):
    if err:
        sys.exit('%s failed: %s \n %s' % (program_name, message, err))
    else:
        sys.exit('%s failed: %s' % (program_name, message))


def help_and_die(parser, message):
    parser.print_help(sys.stderr)
    sys.stderr.write('\n')
    die(message)


def multiple_choice(option, opt_str, value, parser, choices):
    options = value.split(',')
    for opt in options:
        if opt not in choices:
            raise OptionValueError('invalid option %s - valid options are: %s'
                                   % (opt, ', '.join(choices)))
    setattr(parser.values, option.dest, options)


def magnitude_range(option, opt_str, value, parser):
    mag_range = value.split('-')
    if len(mag_range) != 2:
        raise OptionValueError(
            'invalid magnitude %s - valid range is e.g. 6-7' % value)
    try:
        mag_range = tuple(map(float, mag_range))
    except ValueError:
        raise OptionValueError('magnitudes must be numbers.')

    if mag_range[0] > mag_range[1]:
        raise OptionValueError('minimum magnitude must be larger than'
                               ' maximum magnitude.')
    setattr(parser.values, option.dest, mag_range)


def command_scenario(args):

    STORE_STATIC = 'crust2_ib_static'
    STORE_WAVEFORMS = 'crust2_ib'

    def setup(parser):
        parser.add_option(
            '--targets', action='callback', dest='targets', type=str,
            callback=multiple_choice, callback_kwargs={
                'choices': ('waveforms', 'gnss', 'insar')
            },
            default='waveforms',
            help='forward modelling targets for the scenario. Select from:'
                 ' waveforms, gnss and insar. '
                 '(default: --targets=%default,'
                 ' multiple selection by --targets=waveforms,gnss,insar)')
        parser.add_option(
            '--problem', dest='problem', default='cmt',
            type='choice', choices=['cmt', 'rectangular'],
            help='problem to generate: \'dc\' (double couple)'
                 ' or \'rectangular\' (rectangular finite fault)'
                 ' (default: \'%default\')')
        parser.add_option(
            '--magnitude-range', dest='magnitude_range', type=str,
            action='callback', callback=magnitude_range, default=[6.0, 7.0],
            help='Magnitude range min_mag-max_mag (default: %default)')
        parser.add_option(
            '--nstations', dest='nstations', type=int, default=20,
            help='number of seismic stations to create (default: %default)')
        parser.add_option(
            '--gnss_nstations', dest='gnss_nstations', type=int, default=20,
            help='number of GNSS campaign stations to create'
                 ' (default: %default)')
        parser.add_option(
            '--nevents', dest='nevents', type=int, default=1,
            help='number of events to create (default: %default)')
        parser.add_option(
            '--lat', dest='lat', type=float, default=41.0,
            help='center latitude of the scenario (default: %default)')
        parser.add_option(
            '--lon', dest='lon', type=float, default=33.3,
            help='center latitude of the scenario (default: %default)')
        parser.add_option(
            '--radius', dest='radius', type=float, default=200.,
            help='radius of the the scenario in [km] (default: %default)')
        parser.add_option(
            '--gf-waveforms', dest='store_waveforms', type=str,
            default=STORE_WAVEFORMS,
            help='Green\'s function store for waveform modelling, '
                 '(default: %default)')
        parser.add_option(
            '--gf-static', dest='store_statics', type=str,
            default=STORE_STATIC,
            help='Green\'s function store for static modelling, '
                 '(default: %default)')
        parser.add_option(
            '--force', dest='force', action='store_true',
            help='overwrite existing project folder.')

    parser, options, args = cl_parse('scenario', args, setup)

    if len(args) == 1:
        project_dir = args[0]
    else:
        parser.print_help()
        sys.exit(1)

    from grond import scenario as grond_scenario
    try:
        scenario = grond_scenario.GrondScenario(
            project_dir,
            center_lat=options.lat, center_lon=options.lon,
            radius=options.radius*km)

        if 'waveforms' in options.targets:
            obs = grond_scenario.WaveformObservation(
                nstations=options.nstations,
                store_id=options.store_waveforms)
            scenario.add_observation(obs)

        if 'insar' in options.targets:
            obs = grond_scenario.InSARObservation(
                store_id=options.store_statics)
            scenario.add_observation(obs)

        if 'gnss' in options.targets:
            obs = grond_scenario.GNSSCampaignObservation(
                nstations=options.gnss_nstations,
                store_id=options.store_statics)
            scenario.add_observation(obs)

        if options.problem == 'cmt':
            problem = grond_scenario.DCSourceProblem(
                nevents=options.nevents,
                magnitude_min=options.magnitude_range[0],
                magnitude_max=options.magnitude_range[1])
        elif options.problem == 'rectangular':
            problem = grond_scenario.RectangularSourceProblem(
                nevents=options.nevents)
        scenario.set_problem(problem)

        scenario.build(force=options.force, interactive=True)
        logger.info(CLIHints('scenario',
                             config=scenario.get_grond_config_path(),
                             project_dir=project_dir))

    except grond.GrondError as e:
        die(str(e))


def command_init(args):

    from . import cmd_init as init

    def setup(parser):
        parser.add_option(
            '--targets', action='callback', dest='targets', type=str,
            callback=multiple_choice, callback_kwargs={
                'choices': ('waveforms', 'gnss', 'insar')
            },
            default='waveforms',
            help='select from:'
                 ' waveforms, gnss and insar. '
                 '(default: --targets=%default,'
                 ' multiple selection by --targets=waveform,gnss,insar)')
        parser.add_option(
            '--problem', dest='problem', default='cmt',
            type='choice', choices=['cmt', 'rectangular'],
            help='problem to generate: \'dc\' (double couple)'
                 ' or\'rectangular\' (rectangular finite fault)'
                 ' (default: \'%default\')')
        parser.add_option(
            '--full', dest='full', action='store_true',
            help='create a full configuration, from targets above')
        parser.add_option(
            '--force', dest='force', action='store_true',
            help='overwrite existing project folder')

    parser, options, args = cl_parse('init', args, setup)

    try:
        project = init.GrondProject()

        if 'waveforms' in options.targets:
            project.add_waveforms()
            project.set_cmt_source()
        if 'insar' in options.targets:
            project.add_insar()
            project.set_rectangular_source()
        if 'gnss' in options.targets:
            project.add_gnss()
            project.set_rectangular_source()

        if options.full:
            project = init.GrondProject()

            project.add_waveforms()
            project.add_insar()
            project.add_gnss()
            project.set_rectangular_source()

        if options.problem == 'cmt':
            project.set_cmt_source()
        elif options.problem == 'rectangular':
            project.set_rectangular_source()

        if len(args) == 1:
            project_dir = args[0]
            project.build(project_dir, options.force)
            logger.info(CLIHints(
                'init', project_dir=project_dir,
                config=op.join(project_dir, 'config', 'config.gronf')))
        else:
            sys.stdout.write(project.dump())

    except grond.GrondError as e:
        die(str(e))


def command_events(args):
    def setup(parser):
        pass

    parser, options, args = cl_parse('events', args, setup)
    if len(args) != 1:
        help_and_die(parser, 'missing arguments')

    config_path = args[0]
    try:
        config = grond.read_config(config_path)

        for event_name in grond.get_event_names(config):
            print(event_name)

    except grond.GrondError as e:
        die(str(e))


def command_check(args):

    from grond.environment import Environment

    def setup(parser):
        parser.add_option(
            '--target-ids', dest='target_string_ids', metavar='TARGET_IDS',
            help='process only selected targets. TARGET_IDS is a '
                 'comma-separated list of target IDs. Target IDs have the '
                 'form SUPERGROUP.GROUP.NETWORK.STATION.LOCATION.CHANNEL.')

        parser.add_option(
            '--waveforms', dest='show_waveforms', action='store_true',
            help='show raw, restituted, projected, and processed waveforms')

        parser.add_option(
            '--nrandom', dest='n_random_synthetics', metavar='N', type=int,
            default=10,
            help='set number of random synthetics to forward model (default: '
                 '10). If set to zero, create synthetics for the reference '
                 'solution.')

    parser, options, args = cl_parse('check', args, setup)

    try:
        env = Environment(args)
        config = env.get_config()

        target_string_ids = None
        if options.target_string_ids:
            target_string_ids = options.target_string_ids.split(',')

        grond.check(
            config,
            event_names=env.get_selected_event_names(),
            target_string_ids=target_string_ids,
            show_waveforms=options.show_waveforms,
            n_random_synthetics=options.n_random_synthetics)
        logger.info(CLIHints('check', config=env.get_config_path()))

    except grond.GrondError as e:
        die(str(e))


def command_go(args):

    from grond.environment import Environment

    def setup(parser):
        parser.add_option(
            '--force', dest='force', action='store_true',
            help='overwrite existing run directory')
        parser.add_option(
            '--preserve', dest='preserve', action='store_true',
            help='preserve old rundir')
        parser.add_option(
            '--status', dest='status', default='state',
            type='choice', choices=['state', 'quiet'],
            help='status output selection (choices: state, quiet, default: '
                 'state)')
        parser.add_option(
            '--parallel', dest='nparallel', type=int, default=1,
            help='set number of events to process in parallel, '
                 'If set to more than one, --status=quiet is implied.')

    parser, options, args = cl_parse('go', args, setup)

    try:
        env = Environment(args)

        status = options.status
        if options.nparallel != 1:
            status = 'quiet'

        grond.go(
            env,
            force=options.force,
            preserve=options.preserve,
            status=status,
            nparallel=options.nparallel)
        if len(env.get_selected_event_names()) == 1:
            logger.info(CLIHints(
                'go', rundir=env.get_rundir_path()))

    except grond.GrondError as e:
        die(str(e))


def command_forward(args):
    def setup(parser):
        pass

    parser, options, args = cl_parse('forward', args, setup)
    if len(args) < 1:
        help_and_die(parser, 'missing arguments')

    event_names = args[1:]

    if not event_names:
        help_and_die(parser, 'no event names given')

    run_path = args[0]
    grond.forward(
        run_path,
        event_names=event_names)


def command_harvest(args):
    def setup(parser):
        parser.add_option(
            '--force', dest='force', action='store_true',
            help='overwrite existing harvest directory')
        parser.add_option(
            '--neach', dest='neach', type=int, default=10,
            help='take NEACH best samples from each chain (default: %default)')
        parser.add_option(
            '--weed', dest='weed', type=int, default=0,
            help='weed out bootstrap samples with bad global performance. '
                 '0: no weeding (default), '
                 '1: only bootstrap chains where all NEACH best samples '
                 'global misfit is less than the global average misfit of all '
                 'NEACH best in all chains plus one standard deviation are '
                 'included in the harvest ensemble, '
                 '2: same as 1 but additionally individual samples are '
                 'removed if their global misfit is greater than the global '
                 'average misfit of all NEACH best in all chains, '
                 '3: harvesting is done on the global chain only, bootstrap '
                 'chains are excluded')

    parser, options, args = cl_parse('harvest', args, setup)
    if len(args) != 1:
        help_and_die(parser, 'no rundir')

    run_path, = args
    grond.harvest(
        run_path,
        force=options.force,
        nbest=options.neach,
        weed=options.weed)


def command_plot(args):

    import matplotlib
    matplotlib.use('Agg')

    from grond.environment import Environment

    def setup(parser):
        pass

    details = ''

    parser, options, args = cl_parse('plot', args, setup, details)

    if len(args) not in (2, 3):
        help_and_die(parser, 'two or three arguments required')

    env = Environment(args[1:])
    from grond import plot
    if args[0] == 'list':
        plot_names, plot_doc = zip(*[(pc.name, pc.__doc__)
                                     for pc in env.get_plot_classes()])
        plot_descs = [doc.split('\n')[0].strip() for doc in plot_doc]
        left_spaces = max([len(pn) for pn in plot_names])

        for name, desc in zip(plot_names, plot_descs):
            print('{name:<{ls}} - {desc}'.format(
                ls=left_spaces, name=name, desc=desc))

    elif args[0] == 'config':
        plot_config_collection = plot.get_plot_config_collection(env)
        print(plot_config_collection)

    elif args[0] == 'all':
        plot_names = plot.get_plot_names(env)
        plot.make_plots(env, plot_names=plot_names)

    elif op.exists(args[0]):
        plots = plot.PlotConfigCollection.load(args[0])
        plot.make_plots(env, plots)

    else:
        plot_names = [name.strip() for name in args[0].split(',')]
        plot.make_plots(env, plot_names=plot_names)


def command_movie(args):

    import matplotlib
    matplotlib.use('Agg')

    def setup(parser):
        pass

    parser, options, args = cl_parse('movie', args, setup)

    if len(args) != 4:
        help_and_die(parser, 'four arguments required')

    run_path, xpar_name, ypar_name, movie_filename_template = args

    from grond import plot

    movie_filename = movie_filename_template % {
        'xpar': xpar_name,
        'ypar': ypar_name}

    try:
        plot.make_movie(run_path, xpar_name, ypar_name, movie_filename)

    except grond.GrondError as e:
        die(str(e))


def command_export(args):

    def setup(parser):
        parser.add_option(
            '--type', dest='type', metavar='TYPE',
            choices=('event', 'event-yaml', 'source', 'vector'),
            help='select type of objects to be exported. Choices: '
                 '"event" (default), "event-yaml", "source", "vector".')

        parser.add_option(
            '--parameters', dest='parameters', metavar='PLIST',
            help='select parameters to be exported. PLIST is a '
                 'comma-separated list where each entry has the form '
                 '"<parameter>[.<measure>]". Available measures: "best", '
                 '"mean", "std", "minimum", "percentile16", "median", '
                 '"percentile84", "maximum".')

        parser.add_option(
            '--output', dest='filename', metavar='FILE',
            help='write output to FILE')

    parser, options, args = cl_parse('export', args, setup)
    if len(args) < 2:
        help_and_die(parser, 'arguments required')

    what = args[0]

    dirnames = args[1:]

    what_choices = ('best', 'mean', 'ensemble', 'stats')

    if what not in what_choices:
        help_and_die(
            parser,
            'invalid choice: %s (choose from %s)' % (
                repr(what), ', '.join(repr(x) for x in what_choices)))

    if options.parameters:
        pnames = options.parameters.split(',')
    else:
        pnames = None

    try:
        grond.export(
            what,
            dirnames,
            filename=options.filename,
            type=options.type,
            pnames=pnames)

    except grond.GrondError as e:
        die(str(e))


def command_report(args):

    import matplotlib
    matplotlib.use('Agg')

    from grond.environment import Environment
    from grond.report import \
        report, report_index, serve_ip, serve_report, read_config, \
        write_config, ReportConfig

    def setup(parser):
        parser.add_option(
            '--index-only',
            dest='index_only',
            action='store_true',
            help='create index only')
        parser.add_option(
            '--serve', '-s',
            dest='serve',
            action='store_true',
            help='start http service')
        parser.add_option(
            '--serve-external', '-S',
            dest='serve_external',
            action='store_true',
            help='shortcut for --serve --host=default --fixed-port')
        parser.add_option(
            '--host',
            dest='host',
            default='localhost',
            help='<ip> to start the http server on. Special values for '
                 '<ip>: "*" binds to all available interfaces, "default" '
                 'to default external interface, "localhost" to "127.0.0.1".')
        parser.add_option(
            '--port',
            dest='port',
            type=int,
            default=8383,
            help='set default http server port. Will count up if port is '
                 'already in use unless --fixed-port is given.')
        parser.add_option(
            '--fixed-port',
            dest='fixed_port',
            action='store_true',
            help='fail if port is already in use')
        parser.add_option(
            '--open', '-o',
            dest='open',
            action='store_true',
            help='open report in browser')
        parser.add_option(
            '--config',
            dest='config',
            help='report configuration file to use')
        parser.add_option(
            '--write-config',
            dest='write_config',
            metavar='FILE',
            help='write configuration (or default configuration) to FILE')
        parser.add_option(
            '--update-without-plotting',
            dest='update_without_plotting',
            action='store_true',
            help='quick-and-dirty update parameter files without plotting')

    parser, options, args = cl_parse('report', args, setup)

    s_conf = ''
    if options.config:
        try:
            conf = read_config(options.config)
        except grond.GrondError as e:
            die(str(e))

        s_conf = ' --config="%s"' % options.config
    else:
        conf = ReportConfig()
        conf.set_basepath('.')

    if options.write_config:
        try:
            write_config(conf, options.write_config)
            sys.exit(0)

        except grond.GrondError as e:
            die(str(e))

    if len(args) == 1 and op.exists(op.join(args[0], 'index.html')):
        conf.reports_base_path = conf.rel_path(args[0])
        s_conf = ' %s' % args[0]
        args = []

    reports_base_path = conf.expand_path(conf.reports_base_path)

    if options.index_only:
        report_index(conf)
        args = []

    reports_generated = False

    if args and all(op.isdir(rundir) for rundir in args):
        rundirs = args
        all_failed = True
        for rundir in rundirs:
            try:
                env = Environment([rundir])
                report(
                    env, conf,
                    update_without_plotting=options.update_without_plotting)

                all_failed = False
                reports_generated = True

            except grond.GrondError as e:
                logger.error(str(e))

        if all_failed:
            die('no reports generated')

    elif args:
        try:
            env = Environment(args)
            for event_name in env.get_selected_event_names():
                env.set_current_event_name(event_name)
                report(
                    env, conf,
                    update_without_plotting=options.update_without_plotting)

                reports_generated = True

        except grond.GrondError as e:
            die(str(e))

    if options.serve or options.serve_external:
        if options.serve_external:
            host = 'default'
        else:
            host = options.host

        addr = serve_ip(host), options.port

        serve_report(
            addr,
            report_config=conf,
            fixed_port=options.fixed_port or options.serve_external,
            open=options.open)

    elif options.open:
        import webbrowser
        url = 'file://%s/index.html' % op.abspath(reports_base_path)
        webbrowser.open(url)

    else:
        if not reports_generated and not options.index_only:
            logger.info('nothing to do, see: grond report --help')

    if reports_generated and not (options.serve or options.serve_external):
        logger.info(CLIHints('report', config=s_conf))


def command_qc_polarization(args):

    def setup(parser):
        parser.add_option(
            '--time-factor-pre', dest='time_factor_pre', type=float,
            metavar='NUMBER',
            default=0.5,
            help='set duration to extract before synthetic P phase arrival, '
                 'relative to 1/fmin. fmin is taken from the selected target '
                 'group in the config file (default=%default)')
        parser.add_option(
            '--time-factor-post', dest='time_factor_post', type=float,
            metavar='NUMBER',
            default=0.5,
            help='set duration to extract after synthetic P phase arrival, '
                 'relative to 1/fmin. fmin is taken from the selected target '
                 'group in the config file (default=%default)')
        parser.add_option(
            '--distance-min', dest='distance_min', type=float,
            metavar='NUMBER',
            help='minimum event-station distance [m]')
        parser.add_option(
            '--distance-max', dest='distance_max', type=float,
            metavar='NUMBER',
            help='maximum event-station distance [m]')
        parser.add_option(
            '--depth-min', dest='depth_min', type=float,
            metavar='NUMBER',
            help='minimum station depth [m]')
        parser.add_option(
            '--depth-max', dest='depth_max', type=float,
            metavar='NUMBER',
            help='maximum station depth [m]')
        parser.add_option(
            '--picks', dest='picks_filename',
            metavar='FILENAME',
            help='add file with P picks in Snuffler marker format')
        parser.add_option(
            '--save', dest='output_filename',
            metavar='FILENAME.FORMAT',
            help='save output to file FILENAME.FORMAT')
        parser.add_option(
            '--dpi', dest='output_dpi', type=float, default=120.,
            metavar='NUMBER',
            help='DPI setting for raster formats (default=120)')

    parser, options, args = cl_parse('qc-polarization', args, setup)
    if len(args) != 3:
        help_and_die(parser, 'missing arguments')

    if options.output_filename:
        import matplotlib
        matplotlib.use('Agg')

    import grond.qc

    config_path, event_name, target_group_path = args

    try:
        config = grond.read_config(config_path)
    except grond.GrondError as e:
        die(str(e))

    ds = config.get_dataset(event_name)

    engine = config.engine_config.get_engine()

    nsl_to_time = None
    if options.picks_filename:
        markers = marker.load_markers(options.picks_filename)
        marker.associate_phases_to_events(markers)

        nsl_to_time = {}
        for m in markers:
            if isinstance(m, marker.PhaseMarker):
                ev = m.get_event()
                if ev is not None and ev.name == event_name:
                    nsl_to_time[m.one_nslc()[:3]] = m.tmin

        if not nsl_to_time:
            help_and_die(
                parser,
                'no markers associated with event "%s" found in file "%s"' % (
                    event_name, options.picks_filename))

    target_group_paths_avail = []
    for target_group in config.target_groups:
        name = target_group.path
        if name == target_group_path:
            imc = target_group.misfit_config
            fmin = imc.fmin
            fmax = imc.fmax
            ffactor = imc.ffactor

            store = engine.get_store(target_group.store_id)
            timing = '{cake:P|cake:p|cake:P\\|cake:p\\}'

            grond.qc.polarization(
                ds, store, timing, fmin=fmin, fmax=fmax, ffactor=ffactor,
                time_factor_pre=options.time_factor_pre,
                time_factor_post=options.time_factor_post,
                distance_min=options.distance_min,
                distance_max=options.distance_max,
                depth_min=options.depth_min,
                depth_max=options.depth_max,
                nsl_to_time=nsl_to_time,
                output_filename=options.output_filename,
                output_dpi=options.output_dpi)

            return

        target_group_paths_avail.append(name)

        die('no target group with path "%s" found. Available: %s' % (
            target_group_path, ', '.join(target_group_paths_avail)))


def command_upgrade_config(args):
    def setup(parser):
        parser.add_option(
            '--diff', dest='diff', action='store_true',
            help='create diff between normalized old and new versions')

    parser, options, args = cl_parse('upgrade-config', args, setup)
    if len(args) != 1:
        help_and_die(parser, 'missing argument <configfile>')

    from grond import upgrade
    upgrade.upgrade_config_file(args[0], diff=options.diff)


def command_diff(args):
    def setup(parser):
        pass

    parser, options, args = cl_parse('diff', args, setup)
    if len(args) != 2:
        help_and_die(parser, 'requires exactly two arguments')

    from grond.config import diff_configs
    diff_configs(*args)


def command_version(args):
    def setup(parser):
        parser.add_option(
            '--short', dest='short', action='store_true',
            help='only print Grond\'s version number')

    parser, options, args = cl_parse('version', args, setup)

    if options.short:
        print(grond.__version__)
        return

    print("grond: %s" % grond.__version__)

    try:
        import pyrocko
        print('pyrocko: %s' % pyrocko.long_version)
    except ImportError:
        print('pyrocko: N/A')

    try:
        import numpy
        print('numpy: %s' % numpy.__version__)
    except ImportError:
        print('numpy: N/A')

    try:
        import scipy
        print('scipy: %s' % scipy.__version__)
    except ImportError:
        print('scipy: N/A')

    try:
        import matplotlib
        print('matplotlib: %s' % matplotlib.__version__)
    except ImportError:
        print('matplotlib: N/A')

    try:
        from pyrocko.gui.qt_compat import Qt
        print('PyQt: %s' % Qt.PYQT_VERSION_STR)
        print('Qt: %s' % Qt.QT_VERSION_STR)
    except ImportError:
        print('PyQt: N/A')
        print('Qt: N/A')

    import sys
    print('python: %s.%s.%s' % sys.version_info[:3])


if __name__ == '__main__':
    main()
