import random
import hashlib
import hmac
from util import modexp
import time

# NIST prime
N = 0xffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f24117c4b1fe649286651ece45b3dc2007cb8a163bf0598da48361c55d39a69163fa8fd24cf5f83655d23dca3ad961c62f356208552bb9ed529077096966d670c354e4abc9804f1746c08ca237327ffffffffffffffff

# What happens in this protocol?
# 1. The parties agree ahead of time on shared parameters:
# - N a prime modulus
# - g a prime base
# - k a constant (?)
# - the client's email address (identity)
# - the client's password
# 2. The server generates a random salt, hashes the salt and the password, and generates
#    a validator, v = g**x % N., where x is computed from the password and the salt.
# 3. The client computes its public key A as g**a % N, with a the client's secret for
#    this session, and provides both to the server.
# 4. The server computes its own public key as kv + g**b % N with b the server's secret
#    and v the validtor from earlier. The presence of v means that the server's public
#    key will be different for each session with the same client. The server provides
#    salt and B to the client.
#    Why do we need the  
#    validator? Why can't the server just generate a new b?
# 5. Both the client and server can now compute u = SHA256(A|B).
# 6. The client now generates x as SHA256(salt|password) and 
#    S = (B - kg**x)**(a+ux) % N
# 
#    The server now generates
#    S = (Av**u)**b % N
#    I worked out with pencil and paper that SA == SB
def compute_u(A, B):
    sha = hashlib.sha256()
    sha.update(hex(A))
    sha.update(hex(B))
    uH = sha.hexdigest()
    return int(uH, 16)

def compute_x(salt, password):
    sha = hashlib.sha256()
    sha.update(hex(salt))
    sha.update(password)
    xH = sha.hexdigest()
    return int(xH, 16)

class SRPServer:
    '''
    Encapsulates a single SRP key agreement session. For hashing of large numbers
    we will use hex strings like 123af
    '''
    def __init__(self, email, password, N=N, g=2, k=3):
        self.N = N
        self.g = g
        self.k = k
        self.email = email
        self.password = password
        
        self.b = random.randint(0, N)
        self.salt = random.randint(0, 2**32-1)

        x = compute_x(self.salt, password)
        v = modexp(g, x, N)
        self.v = v

    def rcv_msg1(self, email, A):
        self.client_email = email
        self.client_A = A
        
        B = (self.k * self.v + modexp(self.g, self.b, self.N)) % self.N
        self.u = compute_u(A, B)

        part1 = (A * modexp(self.v, self.u, self.N)) % N
        S = modexp(part1, self.b, self.N)
        sha = hashlib.sha256()
        sha.update(hex(S))
        self.K = sha.digest()
        print 'Server S =', S, 'Server K = ', self.K

        return self.salt, B

    def rcv_msg3(self, client_mac):
        true_mac = hmac.new(self.K, hex(self.salt), hashlib.sha256).digest()
        if true_mac == client_mac:
            return 'OK'


class SRPClient:

    def __init__(self, email, password, N=N, g=2, k=3):
        self.N = N
        self.g = g
        self.k = k
        self.email = email
        self.password = password
        
        self.a = random.randint(0, N)
        self.A = modexp(self.g, self.a, self.N)

    def rcv_msg2(self, salt, B):
        self.u = compute_u(self.A, B)
        sha = hashlib.sha256()
        sha.update(hex(salt))
        sha.update(self.password)
        x = compute_x(salt, self.password)
        
        part1 = (B - self.k * modexp(self.g, x, self.N)) % self.N
        S =  modexp(part1, self.a + self.u * x, self.N)
        sha = hashlib.sha256()
        sha.update(hex(S))

        self.K = sha.digest()

        mac = hmac.new(self.K, hex(salt), hashlib.sha256).digest()
        return mac


def compute_x_simple(salt, password):
    sha = hashlib.sha256()
    sha.update(hex(salt))
    sha.update(password)
    return int(sha.hexdigest(), 16)


class SimpleSRPServer:
    def __init__(self, email, password, N=N, g=2):
        self.N = N
        self.g = g
        self.email = email
        self.password = password
        
        self.b = random.randint(0, N)
        self.salt = random.randint(0, 2**32-1)

        self.B = modexp(g, self.b, self.N)

        x = compute_x_simple(self.salt, self.password)
        print 'Server x', x
        self.v = modexp(g, x, self.N)
        self.u = random.randint(0, 2**128-1)
        
    # Assume email is correct
    def rcv_msg1(self, email, A):
        self.A = A
        part1 = A * modexp(self.v, self.u, self.N)
        S = modexp(part1, self.b, self.N)

        sha = hashlib.sha256()
        sha.update(hex(S))
        self.K = sha.digest()
        print 'Simple server K', self.K.encode('hex')

        return self.salt, self.B, self.u
        
    def rcv_msg3(self, client_mac):
        true_mac = hmac.new(self.K, hex(self.salt), hashlib.sha256).digest()
        if true_mac == client_mac:
            return 'OK'


class SimpleSRPClient:

    def __init__(self, email, password, N=N, g=2):
        self.N = N
        self.g = g
        self.email = email
        self.password = password
        
        self.a = random.randint(0, N)
        self.A = modexp(self.g, self.a, self.N)

        print 'The real password is', self.password

    def rcv_msg2(self, salt, B, u):
        self.salt = salt
        self.B = B
        self.u = u
        
        x = compute_x_simple(salt, self.password)
        print 'Simple client salt, password, x', self.salt, self.password, x
        S = modexp(B, self.a + u * x, self.N)
        # This should be g**(a+x) == g**a * g**x == A * g**x
        print 'Simple client S', S

        sha = hashlib.sha256()
        sha.update(hex(S))
        self.K = sha.digest()
        print 'Simple client K', self.K.encode('hex')

        mac = hmac.new(self.K, hex(salt), hashlib.sha256).digest()
        return mac

    def rcv_msg4(self, msg):
        assert msg == 'OK'


class SimpleSRPMITM:
    
    def __init__(self, B=2, u=1, salt=0, g=2):
        self.B = B
        self.u = u
        self.salt = salt
        self.g = g

    def rcv_msg1(self, email, A):
        self.A = A
        return self.salt, self.B, self.u
    
    def rcv_msg3(self, mac):
        p = self.brute_force_srp(mac)
        print 'Cracked password!', p
        exit()

    # A, N, salt integers
    # target a byte string output from HMAC-SHA256
    def brute_force_srp(self, target):
        with open('/usr/share/dict/words') as words:
            count = 0
            start = time.time()
            for w in words:
                w = w.strip()
                if count > 0 and count % 1000 == 0:
                    print 'Tried', count, 'words so far', '(' + str(time.time() - start) + ') s per 1000'
                    print 'Current word', w
                    start = time.time()
                count += 1
                sha1 = hashlib.sha256()
                sha1.update(hex(self.salt))
                sha1.update(w)
                x = compute_x_simple(self.salt, w)
                
                S = (self.A * modexp(self.g, x, N)) % N
                sha2 = hashlib.sha256()
                sha2.update(hex(S))
                K = sha2.digest()

                mac = hmac.new(K, hex(self.salt), hashlib.sha256).digest()
                if mac == target:
                    return w

        raise Exception('No solution found')
