import cPickle as pickle
import numpy as np
import theano
import theano.tensor as T

from theano.tensor.shared_randomstreams import RandomStreams

from theanify import theanify
from deepx.nn import ParameterModel, LSTM, Softmax, load_lstm, load_softmax

class CharacterRNN(ParameterModel):

    def __init__(self, name, encoding, n_hidden=10, n_layers=2):
        super(CharacterRNN, self).__init__(name)
        self.n_hidden = n_hidden
        self.n_layers = n_layers

        self.vocab_size = encoding.index

        self.lstm = LSTM('%s-charrnn' % name, self.vocab_size,
                         n_hidden=self.n_hidden,
                         n_layers=self.n_layers)
        self.output = Softmax('%s-softmax' % name, n_hidden, self.vocab_size)
        self.rng = RandomStreams(seed=1337)

    def save_parameters(self, location):
        state = {
            'n_hidden': self.n_hidden,
            'n_layers': self.n_layers,
            'lstm': self.lstm.state(),
            'output': self.output.state()
        }
        with open(location, 'wb') as fp:
            pickle.dump(state, fp)

    def load_parameters(self, location):
        with open(location, 'rb') as fp:
            state = pickle.load(fp)

        self.n_hidden = state['n_hidden']
        self.n_layers = state['n_layers']
        self.lstm = load_lstm(state['lstm'])
        self.output = load_softmax(state['output'])

    def cost(self, X, state, y):
        _, state, ypred = self.forward(X, state)
        S, N, V = y.shape
        y = y.reshape((S * N, V))
        ypred = ypred.reshape((S * N, V))
        return T.nnet.categorical_crossentropy(ypred, y).mean(), state

    def forward(self, X, state):
        S, N, D = X.shape
        H = self.lstm.n_hidden
        L = self.lstm.n_layers
        O = self.output.n_output

        def step(input, previous_hidden, previous_state, previous_output):
            lstm_hidden, state = self.lstm.forward(input, previous_hidden, previous_state)
            final_output = self.output.forward(lstm_hidden[:, -1, :])
            return lstm_hidden, state, final_output

        hidden = T.unbroadcast(T.alloc(np.array(0).astype(theano.config.floatX), N, L, H), 1)

        (encoder_output, encoder_state, softmax_output), _ = theano.scan(step,
                              sequences=[X],
                              outputs_info=[
                                            hidden,
                                            state,
                                            T.alloc(np.asarray(0).astype(theano.config.floatX),
                                                    N,
                                                    O),
                                           ],
                              n_steps=S)
        return encoder_output, encoder_state, softmax_output

    @theanify(T.fvector('start_token'), T.iscalar('length'), T.fscalar('temperature'), returns_updates=True)
    def generate(self, start_token, length, temperature):
        start_token = start_token[:, np.newaxis].T
        N = 1
        H = self.lstm.n_hidden
        L = self.lstm.n_layers

        def step(input, previous_hidden, previous_state, temperature):
            lstm_hidden, state = self.lstm.forward(input, previous_hidden, previous_state)
            final_output = self.output.forward(lstm_hidden[:, -1, :])
            final_output = final_output + temperature
            final_output /= final_output.sum()
            sample = self.rng.multinomial(n=1, size=(1,), pvals=final_output, dtype=theano.config.floatX)
            return sample, lstm_hidden, state

        hidden = T.unbroadcast(T.alloc(np.array(0).astype(theano.config.floatX), N, L, H), 1)
        state = T.unbroadcast(T.alloc(np.array(0).astype(theano.config.floatX), N, L, H), 1)

        (softmax_output, _, _), updates = theano.scan(step,
                              outputs_info=[
                                            start_token,
                                            hidden,
                                            state,
                                           ],
                              non_sequences=[temperature],
                              n_steps=length)
        return softmax_output[:, 0, :], updates

    def get_parameters(self):
        return self.lstm.get_parameters() + self.output.get_parameters()
