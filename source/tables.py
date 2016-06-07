"""Tables inside the database"""
import copy

from fields import String, Number, Enum, Relation, Set, Record
from rbtree import RBDict


# pylint: disable=no-self-use
class Statistic(Record):
    """Statistics for persons, aliens and items"""
    __slots__ = 'parent', 'name', 'first_train', 'second_train'
    path = 'statistics'
    fields = [
        String('name'),
        Enum('type', ['skill', 'statistic', 'training']),
        String('description')
    ]
    keys = ['name']

    def __init__(self, parent):
        self.parent = parent
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
        if data['name'] not in self.root().statistics:
            return None
        return self.root().statistics[data['name']]

    def removable(self, general):
        """This record cannot be removed savely"""
        return {"statistic": None}


class Action(Record):
    """Actions a person can do in the game"""
    __slots__ = 'parent', 'name', 'difficulty'
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


class Item(Record):
    """Items and some other things in the game"""
    fields = [
        String('name'),
        Enum('type', [
            'profession', 'armor', 'shield', 'weapon', 'gear', 'ammunition',
            'module', 'vehicle', 'trap',
            'body mod', 'weapon mod', 'armor mor', 'vehicle mod',
            'enemy', 'ufo', 'artifact']),
        Set('values', Value)
    ]
    keys = ['type', 'name']

    def __init__(self, parent):
        self.parent = parent


class Game(Record):
    """General record with links to all other records"""
    __slots__ = 'title', 'statistics', 'actions', 'items'
    path = ''
    fields = [
        String('title'),
        Set('statistics', Statistic),
        Set('actions', Action),
        Set('itmes', Item)
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
    Statistic.fields.append(Relation('first_stat', Statistic))
    Statistic.fields.append(Relation('second_stat', Statistic))
    store.init(game)
    store.register(
        Statistic, Action)
    return game
