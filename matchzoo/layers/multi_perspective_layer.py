"""An implementation of MultiPerspectiveLayer for Bimpm model."""

from keras import layers
from keras import backend as K
from keras.engine.topology import Layer

from matchzoo import utils


class MultiPerspectiveLayer(Layer):
    """
    A keras implementation of Bimpm multi-perspective layer.

    For detailed information, see Bilateral Multi-Perspective
    Matching for Natural Language Sentences, section 3.2.
    """

    def __init__(
        self,
        dim_output: int,
        dim_embedding: int,
        perspective: dict={'full': True,
                           'maxpooling': True,
                           'attentive': True,
                           'max-attentive': True},
        **kwargs
    ):
        """
        Class initialization.

        :param output_dim: dimensionality of output space.
        """
        self._dim_output = dim_output
        self._dim_embedding = dim_embedding
        self._perspective = perspective
        super(MultiPerspectiveLayer, self).__init__(**kwargs)

        @classmethod
        def list_available_perspectives(cls) -> list:
            """List available strategy for multi-perspective matching."""
            return ['full', 'maxpooling', 'attentive', 'max-attentive']

        @property
        def num_perspective(self):
            """Get the number of perspectives that is True."""
            return sum(self._perspective.values())
        
        @property
        def perspective(self):
            """Get the perspective status."""
            return self._perspective

        def build(self, input_shape: list):
            """Input shape."""
            # The shape of the weights is l * d
            # l is number of perspectives, d is the dimensionality of embedding.
            if self._perspective.get('full'):
                self.full = self.add_weight(name='pool',
                                            shape=(1,
                                                   self._dim_embedding),
                                            initializer='uniform',
                                            trainable=True)
            if self._perspective.get('maxpooling'):
                self.maxp = self.add_weight(name='maxpooling',
                                            shape=(1,
                                                   self._dim_embedding),
                                            initializer='uniform',
                                            trainable=True)
            if self._perspective.get('attentive'):
                self.atte = self.add_weight(name='attentive',
                                            shape=(1,
                                                   self._dim_embedding),
                                            initializer='uniform',
                                            trainable=True)
            if self._perspective.get('max-attentive'):
                self.maxa = self.add_weight(name='max-attentive',
                                            shape=(1,
                                                   self._dim_embedding),
                                            initializer='uniform',
                                            trainable=True)
            super(MultiPerspectiveLayer, self).build(input_shape)

    def call(self, x: list):
        """Call."""
        seq_lt, seq_rt = x
        # unpack seq_left and seq_right
        # all hidden states, last hidden state of forward pass, last cell state of
        # forward pass, last hidden state of backward pass, last cell state of backward pass.
        lstm_lt, forward_h_lt, _, backward_h_lt, _ = seq_lt
        lstm_rt, forward_h_rt, _, backward_h_rt, _ = seq_rt

        if self._perspective.get('full'):
            # each forward & backward contextual embedding compare
            # with the last step of the last time step of the other sentence.
            # v1 use w_k (d vector) multiply all hidden states `lstm_lt`.
            # v2 & v3 use w_k (d vector) multiply forward_h_rt and backward_h_rt.
            v1 = utils.tensor_mul_tensors_reduce_dim(tensor=self.full,
                                                     tensors=lstm_lt) # tensor.
            v2 = layers.multiply([self.full, forward_h_rt])
            v3 = layers.multiply([self.full, backward_h_rt])
            # cosine similarity
            full_matching_fwd = layers.dot([v1, v2], normalize=True)
            full_matching_bwd = layers.dot([v1, v3], normalize=True)
        if self._perspective.get('maxpooling'):
            # each contextual embedding compare with each contextual embedding.
            # retain the maximum of each dimension.
            # v1 & v2 use weight * list of hidden states, reain max value
            # across each dimension, and result in tensor.
            # forward ans backward compute at the same time.
            v1 = utils.tensor_mul_tensors_with_max_pooling(tensor=self.maxp,
                                                           tensors=lstm_lt)
            v2 = utils.tensor_mul_tensors_with_max_pooling(tensor=self.maxp,
                                                           tensors=lstm_rt)
            maxpooling_matching = layers.dot([v1, v2], normalize=True)
        if self._perspective.get('attentive'):
            # each contextual embedding compare with each contextual embedding.
            # retain sum of weighted mean of each dimension.
            pass
        if self._perspective.get('max-attentive'):
            # each contextual embedding compare with each contextual embedding.
            # retain max of weighted mean of each dimension.
            pass

        return out

    def compute_output_shape(self, input_shape: list):
        shape_a, shape_b = input_shape
        return [(shape_a[0], self._dim_output), shape_b[:-1]]
