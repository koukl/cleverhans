from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from cleverhans.attacks import FastGradientMethod
from cleverhans.defenses import LossXEntropy, LossMixUp, LossFeaturePairing
from cleverhans.devtools.checks import CleverHansTest
from cleverhans.model import Model
import numpy as np
import tensorflow as tf


class SimpleModel(Model):
    """
    A very simple neural network
    """

    def __init__(self, scope='simple', nb_classes=2, **kwargs):
        del kwargs
        Model.__init__(self, scope, nb_classes, locals())

    def fprop(self, x, **kwargs):
        del kwargs
        with tf.variable_scope(self.scope, reuse=tf.AUTO_REUSE):
            w1 = tf.constant([[1.5, .3], [-2, 0.3]],
                             dtype=tf.as_dtype(x.dtype))
            w2 = tf.constant([[-2.4, 1.2], [0.5, -2.3]],
                             dtype=tf.as_dtype(x.dtype))
        h1 = tf.nn.sigmoid(tf.matmul(x, w1))
        res = tf.matmul(h1, w2)
        return {self.O_FEATURES: [h1, res],
                self.O_LOGITS: res,
                self.O_PROBS: tf.nn.softmax(res)}


class TestDefenses(CleverHansTest):
    def setUp(self):
        super(TestDefenses, self).setUp()
        self.model = SimpleModel()
        self.vx = np.array(((1, -1), (-1, 1)), 'f')
        self.vy = np.array(((1, 0), (0, 1)), 'f')
        self.x = tf.placeholder(tf.float32, [None, 2], 'x')
        self.y = tf.placeholder(tf.float32, [None, 2], 'y')

    def test_xe(self):
        loss = LossXEntropy(self.model, smoothing=0.)
        l = loss.fprop(self.x, self.y)
        with tf.Session() as sess:
            vl1 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
            vl2 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
        self.assertClose(vl1, [2.210599660, 1.53666997], atol=1e-6)
        self.assertClose(vl2, [2.210599660, 1.53666997], atol=1e-6)

    def test_xe_smoothing(self):
        loss = LossXEntropy(self.model, smoothing=0.1)
        l = loss.fprop(self.x, self.y)
        with tf.Session() as sess:
            vl1 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
            vl2 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
        self.assertClose(vl1, [2.10587597, 1.47194624], atol=1e-6)
        self.assertClose(vl2, [2.10587597, 1.47194624], atol=1e-6)

    def test_mixup(self):
        def eval_loss(l, count=1000):
            with tf.Session() as sess:
                vl = np.zeros(2, 'f')
                for it in range(count):
                    vl += sess.run(l, feed_dict={self.x: self.vx,
                                                 self.y: self.vy})
            return vl / count

        loss = LossMixUp(self.model, beta=1.)
        vl = eval_loss(loss.fprop(self.x, self.y))
        self.assertClose(vl, [1.23, 1.23], atol=5e-2)

        loss = LossMixUp(self.model, beta=0.5)
        vl = eval_loss(loss.fprop(self.x, self.y))
        self.assertClose(vl, [1.40, 1.40], atol=5e-2)

    def test_feature_pairing(self):
        fgsm = FastGradientMethod(self.model)
        attack = lambda x: fgsm.generate(x)
        loss = LossFeaturePairing(self.model, weight=0.1, attack=attack)
        l = loss.fprop(self.x, self.y)
        with tf.Session() as sess:
            vl1 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
            vl2 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
        self.assertClose(vl1, [4.296023369, 2.963884830], atol=1e-6)
        self.assertClose(vl2, [4.296023369, 2.963884830], atol=1e-6)

        loss = LossFeaturePairing(self.model, weight=10., attack=attack)
        l = loss.fprop(self.x, self.y)
        with tf.Session() as sess:
            vl1 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
            vl2 = sess.run(l, feed_dict={self.x: self.vx, self.y: self.vy})
        self.assertClose(vl1, [4.333082676, 3.00094414], atol=1e-6)
        self.assertClose(vl2, [4.333082676, 3.00094414], atol=1e-6)


if __name__ == '__main__':
    unittest.main()