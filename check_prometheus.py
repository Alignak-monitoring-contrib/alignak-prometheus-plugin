#!/usr/bin/env python

import sys
import argparse

import urllib
from prometheus_client.parser import text_fd_to_metric_families


PLUGIN_NAME = "check_fake"
VERSION = "0.1"
STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3
STATE_DEPENDENT = 4

STATES = {0: 'OK',
          1: 'WARNING',
          2: 'CRITICAL',
          3: 'UNKNOWN',
          4: 'DEPENDENT',
          }


def get_data(args):
    """Fetch data
    """
    exit_code = None
    value = ''
    warning = ''
    critical = ''
    min_value = ''
    max_value = ''
    unit = ''

    found = False

    url = "http://%s:%s/metrics" % (args.hostname, args.port)
    if args.collector is not None:
        metric_name = '%s%s' % (args.metric, args.collector)
    else:
        metric_name = args.metric

    # metric.sample == [(metric_name, {u'host': u'example', u'unit': u'example_unit'}, value)]

    try:
        for metric in text_fd_to_metric_families(urllib.urlopen(url)):
            if metric.name == metric_name:
                value = float(metric.samples[0][2])
                unit = metric.samples[0][1].get('unit', '')
                found = True
            elif metric.name == '%s_warning' % metric_name:
                warning = float(metric.samples[0][2])
            elif metric.name == '%s_critical' % metric_name:
                critical = float(metric.samples[0][2])
            elif metric.name == '%s_min' % metric_name:
                min_value = float(metric.samples[0][2])
            elif metric.name == '%s_max' % metric_name:
                max_value = float(metric.samples[0][2])
            elif args.collector is not None and metric.name == 'nagios_state%s_state' % args.collector:
                exit_code = int(metric.samples[0][2])
    except IOError as err:
        print "UNKNOWN: Error while fetching metric %s: %s" % (metric_name, err)
        sys.exit(3)
    except ValueError as err:
        print "UNKNOWN: Error while fetching metric %s: %s" % (metric_name, err)
        sys.exit(3)

    if not found:
        print "UNKNOWN: Metric %s not found" % metric_name
        sys.exit(3)

    if args.warning is not None:
        warning = args.warning

    if args.critical is not None:
        critical = args.critical

    perf = '%s=%s%s;%s;%s;%s;%s' % (metric_name, value, unit,
                                    warning, critical, min_value, max_value)

    # Set output
    if exit_code is None:
        if critical != '' and value >= critical:
            exit_code = 2
        elif warning != '' and value >= warning:
            exit_code = 1
        else:
            exit_code = 0  # Assume OK as we managed to fetch metric

    state = STATES[exit_code]
    output = "Metric %s fetched successfully" % metric_name
    output = "%s: %s | %s" % (state, output, perf)
    print output
    sys.exit(exit_code)


def main():

    parser = argparse.ArgumentParser(version='%(prog)s ' + VERSION)

    parser.add_argument('-H', '--hostname', dest='hostname', type=str, default="127.0.0.1",
                        help='Hostname to check metrics from')
    parser.add_argument('-p', '--port', dest='port', help='Port for HTTP /metrics. Default 9126',
                        default="9126", type=str)
    parser.add_argument('-m', '--metric', dest='metric', type=str, required=True,
                        help='Metric to fetch')
    parser.add_argument('-C', '--collector', dest='collector', type=str, default=None,
                        help='When executing nagios plugin through telegraf you can acces exit code'
                             'You will have a nagios_*collector* metric for exit code'
                             'The collector variable is also a suffix metric : metric<suffix>')
    parser.add_argument('-w', '--warning', dest='warning', type=float,
                        help='Warning threshold, will override any warning value fetched')
    parser.add_argument('-c', '--critical', dest='critical', type=float,
                        help='Critical threshold, will override any critical value fetched')


    args = parser.parse_args()

    get_data(args)


if __name__ == "__main__":
    main()
