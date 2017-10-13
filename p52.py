from util import *
from itertools import combinations

class IteratedHash(object):

    def __init__(self, c, h):
        '''
        h is just 2 bytes of state. 
        c is a function that takes 1 byte and len(h) state bytes to len(h) random bytes.
        '''
        self.h = h
        self.c = c

    def update(self, m):
        for b in m:
            self.h = self.c(b, self.h)
        return self
    
    def digest(self):
        return self.h
    
    def clone(self):
        new = IteratedHash(self.c, self.h)
        return new
    
    def state(self):
        return self.h


class AESCompressor(object):
    
    def __init__(self, blocksize, rounds):
        assert 0 <= blocksize <= 16
        self.bs = blocksize
        self.rounds = rounds

    def __call__(self, c, k):
        assert self.rounds > 0
        assert len(k) == self.bs
        assert len(c) == 1
        
        rounds = self.rounds
        result = None
        while rounds > 0:
            k_pad = k + (16 - len(k)) * '\x00'
            c_pad = c + 15 * '\x00'
            result = ecb_encrypt(c_pad, k_pad)[:self.bs]
            k = result
            rounds -= 1
        return result

class AESHash(IteratedHash):

    def __init__(self, h='\xff\xff', rounds=1):
        super(AESHash, self).__init__(AESCompressor(len(h), rounds), h)


def generate_collisions(hash_factory, n):
    '''
    Generate 2^n collisions
    '''
    collisions = []
    hash_to_inputs = {}
    i = 1
    while len(collisions) < 2**n:
        hasher = hash_factory()
        if i < 2**8:
            st = num_to_str(i, 8)
        elif i < 2**16:
            st = num_to_str(i, 16)
        elif i < 2**24:
            st = num_to_str(i, 24)
        elif i < 2**32:
            st = num_to_str(i, 32)
        hsh = hasher.update(st).digest()
        if hsh in hash_to_inputs:
            assert st not in hash_to_inputs[hsh]
            for c in hash_to_inputs[hsh]:
                yield (c, st)
                collisions.append((c, st))
            hash_to_inputs[hsh].add(st)
        else:
            hash_to_inputs[hsh] = set([st])
        i += 1


if __name__ == '__main__':
    state = '\xff'
    f = lambda : AESHash(h=state)
    g = lambda : AESHash(h=state, rounds=2)
    
    n = 16
    f_collisions = generate_collisions(f, n)
    for c in f_collisions:
        g1 = g().update(c[0]).digest()
        g2 = g().update(c[1]).digest()
        print g1.encode('hex'), g2.encode('hex')
        if g1 == g2:
            print 'Found collision in g!', c, '->', g1.encode('hex')
            break