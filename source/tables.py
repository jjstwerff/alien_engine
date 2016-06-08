"""Tables inside the database"""
import copy

from fields import String, Number, Enum, Relation, Set, Record
from rbtree import RBDict


# pylint: disable=no-self-use
class Statistic(Record):
    """Statistics for persons, aliens and items"""
    path = 'statistics'
    fields = [
        Enum('type', ['training', 'skill', 'statistic']),
        String('name'),
        String('description')
    ]
    keys = ['type', 'name']

    def __init__(self, parent):
        self.parent = parent
        self.type = None
        self.name = None
        self.first_train = None
        self.second_train = None
        self.description = None

    def store(self):
        """Store the Automatic"""
        self.parent.statistics[self.get_id()] = self

    def remove(self):
        """Remove the Automatic from the index"""
        del self.parent.statistics[self.get_id()]

    def find(self, data):
        """Find the record with the relation key"""
        key = "{:07d}".format(self.field('type').read(data['type'])) + \
              "|" + data['name']
        if key not in self.root().statistics:
            return None
        return self.root().statistics[key]

    def removable(self, general):
        """This record cannot be removed savely"""
        return {"statistic": None}


class Action(Record):
    """Actions a person can do in the game"""
    path = 'actions'
    fields = [
        String('name'),
        String('description')
    ]
    keys = ['name']

    def __init__(self, parent):
        self.parent = parent
        self.name = None

    def store(self):
        """Store the Automatic"""
        self.parent.actions[self.get_id()] = self

    def remove(self):
        """Remove the Automatic from the index"""
        del self.parent.actions[self.get_id()]

    def find(self, data):
        """Find the record with the relation key"""
        if data['name'] not in self.root().actions:
            return None
        return self.root().actions[data['name']]

    def removable(self, general):
        """This record cannot be removed savely"""
        return {"action": None}


class Value(Record):
    """Value of a statistic on an item"""
    fields = [
        Relation('statistic', Statistic),
        Number('value')
    ]
    keys = ['statistic']

    def __init__(self, parent):
        self.parent = parent
        self.statistic = None
        self.value = 0

    def store(self):
        """Store the Automatic"""
        self.parent.values[self.get_id()] = self

    def remove(self):
        """Remove the Automatic from the index"""
        del self.parent.values[self.get_id()]

    def find(self, data):
        """Find the record with the relation key"""
        if data['name'] not in self.root().statistics:
            return None
        item = self.root().items[data['type'] + "|" + data['name']]
        return item.values[data['statistic']]

    def removable(self, general):
        """This record cannot be removed savely"""
        return None


class Item(Record):
    """Items and some other things in the game"""
    fields = [
        Enum('type', [
            'profession', 'armor', 'shield', 'weapon', 'gear', 'ammunition',
            'module', 'vehicle', 'trap',
            'body mod', 'weapon mod', 'armor mor', 'vehicle mod',
            'enemy', 'ufo', 'artifact']),
        String('name'),
        Set('values', Value)
    ]
    keys = ['type', 'name']

    def __init__(self, parent):
        self.parent = parent
        self.type = 0
        self.name = None
        self.values = RBDict()

    def store(self):
        """Store the Automatic"""
        self.parent.items[self.get_id()] = self

    def remove(self):
        """Remove the Automatic from the index"""
        del self.parent.items[self.get_id()]

    def find(self, data):
        """Find the record with the relation key"""
        if data['name'] not in self.root().statistics:
            return None
        return self.root().items[data['type'] + "|" + data['name']]

    def removable(self, general):
        """This record cannot be removed savely"""
        return {"statistic": None}


class Game(Record):
    """General record with links to all other records"""
    path = ''
    fields = [
        String('title'),
        Set('statistics', Statistic),
        Set('actions', Action),
        Set('items', Item)
    ]
    keys = []

    def __init__(self, store):
        self.stored = store
        self.title = ''
        self.statistics = RBDict()
        self.actions = RBDict()
        self.items = RBDict()

    def store(self):
        """This this the top level element"""
        pass

    def remove(self):
        """The top level element cannot be removed"""
        if self.stored.remember_changes:
            if getattr(self.stored, 'changed') is None:
                setattr(self.stored, 'changed', copy.copy(self))
        else:
            setattr(self.stored, 'changed', copy.copy(self))

    def removable(self, general):
        """This record cannot be removed savely"""
        return {"general": None}


def tables_init(store):
    """Add some fields that are forward definitions"""
    game = Game(store)
    Statistic.fields.append(Relation('first_train', Statistic))
    Statistic.fields.append(Relation('second_train', Statistic))
    store.init(game)
    store.register(
        Statistic, Action, Item, Value)
    return game
