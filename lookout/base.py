from collections import defaultdict
import os
import re

from django.utils.importlib import import_module


# Sprint.ly colors

SPRINTLY_DEFAULT_COLOR = '#84b431' # Sprint.ly green
SPRINTLY_STORY_COLOR = '#96be60'
SPRINTLY_TASK_COLOR = '#454545'
SPRINTLY_DEFECT_COLOR = '#D94949'
SPRINTLY_TEST_COLOR = '#5A96AB'

SPRINTLY_COLORS = defaultdict(lambda: SPRINTLY_DEFAULT_COLOR, {
    'story': SPRINTLY_STORY_COLOR,
    'task': SPRINTLY_TASK_COLOR,
    'defect': SPRINTLY_DEFECT_COLOR,
    'test': SPRINTLY_TEST_COLOR
})


class ServiceBase(object):
    def __init__(self, options):
        self.options = options

    def send(self, payload):
        raise NotImplementedError

    @property
    def name(self):
        return self.__class__.__module__.split('.')[-1]

    @property
    def title(self):
        return self.__doc__.split('\n')[1].strip()

    @property
    def description(self):
        return '\n'.join([l.strip() for l in self.__doc__.split('\n')[2:]]).strip()

class MessageServiceBase(object):
    MENTION_RE = r'@\[(?P<name>[^\]]+)\]\(pk:\d+\)'
    MENTION_SUB = r'\g<name>'

    @staticmethod
    def comment(attr):
        return '%s %s. commented "%s" on %s "%s" (#%s) %s' % (
            attr['created_by']['first_name'],
            attr['created_by']['last_name'][0],
            '%s...' % MessageServiceBase._clean_mentions(attr['body'])[0:50],
            attr['item']['type'],
            attr['item']['title'],
            attr['item']['number'],
            attr['item']['short_url'])

    @staticmethod
    def item(attr):
        message = '%s %s. created the %s "%s" (#%s) %s' % (
            attr['created_by']['first_name'],
            attr['created_by']['last_name'][0],
            attr['type'],
            attr['title'],
            attr['number'],
            attr['short_url'])

        if attr['assigned_to'] and \
            attr['assigned_to']['id'] != \
            attr['created_by']['id']:
            message += ' and assigned it to %s %s.' % (
                attr['assigned_to']['first_name'],
                attr['assigned_to']['last_name'][0])
        return message

    @staticmethod
    def block(attr):
        message = '%s %s. indicated the %s "%s" (#%s) %s is blocked on the %s ' \
                  '"%s" (#%s) %s' % (
            attr['user']['first_name'],
            attr['user']['last_name'][0],
            attr['blocked']['type'],
            attr['blocked']['title'],
            attr['blocked']['number'],
            attr['blocked']['short_url'],
            attr['item']['type'],
            attr['item']['title'],
            attr['item']['number'],
            attr['item']['short_url'])
        if attr['item']['assigned_to']:
            message += ', which is owned by %s %s.' % (
                attr['item']['assigned_to']['first_name'],
                attr['item']['assigned_to']['last_name'][0])
        return message

    @staticmethod
    def favorite(attr):
        message = '%s %s. favorited the %s "%s" (#%s) %s' % (
            attr['user']['first_name'],
            attr['user']['last_name'][0],
            attr['item']['type'],
            attr['item']['title'],
            attr['item']['number'],
            attr['item']['short_url'])
        return message

    @staticmethod
    def deploy(attr):
        message = '%s %s. deployed %s items to %s.' % (
            attr['user']['first_name'],
            attr['user']['last_name'][0],
            len(attr['items']),
            attr['environment'])
        return message

    @staticmethod
    def message(payload):
        model = payload['model']
        attr = payload['attributes']
        return getattr(MessageServiceBase, model.lower(), lambda x: None)(attr)

    @staticmethod
    def _clean_mentions(comment):
        """
        Convert @mentions in `comment` of the form "@[Name](pk:123)" to just "Name".
        """
        return re.sub(MessageServiceBase.MENTION_RE,
                      MessageServiceBase.MENTION_SUB, comment)

    @staticmethod
    def format_name(data):
        """
        Takes a dict of user data containing `first_name` and `last_name` keys and returns a formatted name like: John D.
        """
        return '%s %s.' % (data['first_name'], data['last_name'][0])

def get_available_services():
    path = '%s/services' % os.path.dirname(__file__)
    services = {}
    for service_file in os.listdir(path):
        if service_file.endswith('.pyc') or service_file.startswith('__') or \
            service_file.startswith('.'):
            continue

        service_name = service_file.split('.')[0]
        if not service_name:
            continue

        try:
            module = import_module('lookout.services.%s' % service_name)
            services[service_name] = module.Service
        except ImportError:
            continue

    return services
