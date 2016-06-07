"""Simple tree-like structure"""
import copy


class DictIter(object):
    """Iterator through the tree"""
    __slots__ = 'data', 'keys', 'index'

    def __init__(self, data):
        self.data = data
        self.keys = sorted(data.keys())
        self.index = -1  # ready to iterate on the next() call

    def __next__(self):
        """ Return the next item in the container
            Once we go off the list we stay off even if the list changes
        """
        self.index += 1
        if self.index >= len(self.keys):
            raise StopIteration
        return self.data[self.keys[self.index]]


class RBDict(object):
    """Sorted dictionary"""
    __slots__ = 'data', 'changed'

    def __init__(self, initial=None, changes=False):
        self.data = {}
        if changes:
            self.changed = {}
        else:
            self.changed = None
        if initial:
            for key, value in initial.items():
                self[key] = value

    def remember_changes(self, remember_changes=True):
        """Start or stop remembering changes on this Set"""
        self.changed = {} if remember_changes else None

    def changes(self):
        """Get the list of changes with old and new value, clear the changes"""
        if self.changes is None:
            raise AttributeError("No change recoding supported on this Set")
        res = [(
            self.changed[chkey],
            self.data[chkey] if chkey in self.data else None
        ) for chkey in sorted(self.changed.keys())]
        self.changed.clear()
        return res

    def has_changes(self):
        """Return if there are changes in this rbtree"""
        return self.changed is not None and len(self.changed) > 0

    def restore(self, key):
        """Try to restore the old changed record"""
        if self.changed is not None and key in self.changed:
            self.data[key] = self.changed[key]
            del self.changed[key]

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        if self.changed is not None and key not in self.changed:
            if key in self.data:
                raise ValueError("Remove an item before storing a changed one")
            self.changed[key] = None
        self.data[key] = value

    def __delitem__(self, key):
        if self.changed is not None and key not in self.changed:
            if key in self.data:
                self.changed[key] = copy.copy(self.data[key])
        del self.data[key]

    def get(self, key, default=None):
        """Get a key from the dictionary with a default"""
        if key in self.data:
            return self.data[key]
        return default

    def __iter__(self):
        return DictIter(self.data)

    def __len__(self):
        return len(self.data)

    def keys(self):
        """Return all keys"""
        return sorted(self.data.keys())

    def values(self):
        """Return all values"""
        return [self.data[k] for k in self.keys()]

    def items(self):
        """Return all items"""
        return [(k, self.data[k]) for k in self.keys()]

    def __contains__(self, key):
        return key in self.data

    def clear(self):
        """delete all entries"""
        self.data.clear()
        if self.changed is not None:
            self.changed.clear()

    def copy(self):
        """return shallow copy"""
        # there may be a more efficient way of doing this
        return RBDict(self)

    def update(self, other):
        """Add all items from the supplied mapping to this one.
        Will overwrite old entries with new ones."""
        for key in other.keys():
            self[key] = other[key]

    def __repr__(self):
        ls = ['{']
        for k, v in self.items():
            if len(ls) > 1:
                ls.append(', ')
            ls.append(k)
            ls.append('=')
            ls.append(str(v))
        ls.append('}')
        return ''.join(ls)
