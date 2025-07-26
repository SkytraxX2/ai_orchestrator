import numpy as np
class SimpleNN:
    def __init__(self, sizes):
        self.weights = [np.random.randn(y,x) for x,y in zip(sizes[:-1], sizes[1:])]
        self.biases = [np.random.randn(y,1) for y in sizes[1:]]
    def feedforward(self, a):
        for b, w in zip(self.biases, self.weights):
            a = sigmoid(np.dot(w, a) + b)
        return a
def sigmoid(z): return 1.0/(1.0+np.exp(-z))
