import logging
import numpy as np
import theano.tensor as T

from theanify import theanify

from model import ParameterModel

def LSTMLayer(*args):
    class LSTMLayer(ParameterModel):

        def __init__(self, name, n_input, n_output,
                    use_forget_gate=True,
                    use_input_peep=False, use_output_peep=False, use_forget_peep=False,
                    use_tanh_output=True, seed=None):
            super(LSTMLayer, self).__init__(name)

            self.n_input = n_input
            self.n_output = n_output

            self.use_forget_gate = use_forget_gate
            self.use_input_peep = use_input_peep
            self.use_output_peep = use_output_peep
            self.use_forget_peep = use_forget_peep
            self.use_tanh_output = use_tanh_output

            np.random.seed(seed)

            self.init_parameter('W_ix', self.initialize_weights((self.n_input, self.n_output)))
            self.init_parameter('U_ih', self.initialize_weights((self.n_output, self.n_output)))
            self.init_parameter('b_i', self.initialize_weights((self.n_output,)))

            self.init_parameter('W_ox', self.initialize_weights((self.n_input, self.n_output)))
            self.init_parameter('U_oh', self.initialize_weights((self.n_output, self.n_output)))
            self.init_parameter('b_o', self.initialize_weights((self.n_output,)))

            self.init_parameter('W_fx', self.initialize_weights((self.n_input, self.n_output)))
            self.init_parameter('U_fh', self.initialize_weights((self.n_output, self.n_output)))
            self.init_parameter('b_f', self.initialize_weights((self.n_output,)))

            self.init_parameter('W_gx', self.initialize_weights((self.n_input, self.n_output)))
            self.init_parameter('U_gh', self.initialize_weights((self.n_output, self.n_output)))
            self.init_parameter('b_g', self.initialize_weights((self.n_output,)))

            if self.use_input_peep:
                self.init_parameter('P_i', self.initialize_weights((self.n_output, self.n_output)))
            if self.use_output_peep:
                self.init_parameter('P_o', self.initialize_weights((self.n_output, self.n_output)))
            if self.use_forget_peep:
                self.init_parameter('P_f', self.initialize_weights((self.n_output, self.n_output)))

        @theanify(T.matrix('X'), T.matrix('previous_hidden'), T.matrix('previous_state'))
        def step(self, X, previous_hidden, previous_state):
            """
            Parameters:
                X               - B x D (B is batch size, D is dimension)
                previous_hidden - B x O (B is batch size, O is output size)
                previous_state  - B x O (B is batch size, O is output size)
            Returns:
                output          - B x O
                state           - B x O
            """
            Wi = self.get_parameter('W_ix')
            Wo = self.get_parameter('W_ox')
            if self.use_forget_gate:
                Wf = self.get_parameter('W_fx')
            Wg = self.get_parameter('W_gx')

            Ui = self.get_parameter('U_ih')
            Uo = self.get_parameter('U_oh')
            Uf = self.get_parameter('U_fh')
            Ug = self.get_parameter('U_gh')

            bi = self.get_parameter('b_i')
            bo = self.get_parameter('b_o')
            bf = self.get_parameter('b_f')
            bg = self.get_parameter('b_g')

            if self.use_input_peep:
                Pi = self.get_parameter('P_i')
                input_gate = T.nnet.sigmoid(T.dot(X, Wi) + T.dot(previous_hidden, Ui) + T.dot(previous_state, Pi) + bi)
            else:
                input_gate = T.nnet.sigmoid(T.dot(X, Wi) + T.dot(previous_hidden, Ui) + bi)
            candidate_state = T.tanh(T.dot(X, Wg) + T.dot(previous_hidden, Ug) + bg)

            if self.use_forget_gate:
                if self.use_forget_peep:
                    Pf = self.get_parameter('P_f')
                    forget_gate = T.nnet.sigmoid(T.dot(X, Wf) + T.dot(previous_hidden, Uf) + T.dot(previous_state, Pf) + bf)
                else:
                    forget_gate = T.nnet.sigmoid(T.dot(X, Wf) + T.dot(previous_hidden, Uf) + bf)
                state = candidate_state * input_gate + previous_state * forget_gate
            else:
                state = candidate_state * input_gate + previous_state * 0

            if self.use_output_peep:
                Po = self.get_parameter('P_o')
                output_gate = T.nnet.sigmoid(T.dot(X, Wo) + T.dot(previous_hidden, Uo) + T.dot(previous_state, Po) + bo)
            else:
                output_gate = T.nnet.sigmoid(T.dot(X, Wo) + T.dot(previous_hidden, Uo) + bo)
            if self.use_tanh_output:
                output = output_gate * T.tanh(state)
            else:
                output = output_gate * state
            return output, state

        def state(self):
            state_params = {}
            for param, value in self.parameters.items():
                state_params[param] = value.get_value()
            return {
                'name': self.name,
                'n_input': self.n_input,
                'n_output': self.n_output,
                'use_forget_gate': self.use_forget_gate,
                'use_input_peep' : self.use_input_peep,
                'use_output_peep' : self.use_output_peep,
                'use_forget_peep' : self.use_forget_peep,
                'use_tanh_output' : self.use_tanh_output,
                'parameters': state_params
            }

        @classmethod
        def load(cls, state):
            layer = cls(state['name'], state['n_input'], state['n_output'],
                        use_forget_gate=state['use_forget_gate'],
                        use_input_peep=state['use_input_peep'],
                        use_output_peep=state['use_output_peep'],
                        use_forget_peep=state['use_forget_peep'],
                        use_tanh_output=state['use_tanh_output'],
                        )
            for param, value in state['parameters'].items():
                layer.set_parameter_value(param, value)
            return layer
    return LSTMLayer(*args)
