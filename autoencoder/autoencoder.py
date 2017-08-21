#!/usr/bin/python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

"""
Authors:    Dario Cazzani
"""
import sys
sys.path.append('../')
from config import set_config
from helpers.misc import check_tf_version, extend_options

import subprocess
import tensorflow as tf
import numpy as np
import datetime
import glob
import os
import matplotlib.pyplot as plt
from matplotlib import gridspec
from tensorflow.examples.tutorials.mnist import input_data

# Get the MNIST data
mnist = input_data.read_data_sets('./Data', one_hot=True)

# Parameters
input_dim = 784
hidden_layer1 = 1000
hidden_layer2 = 1000

def generate_image_grid(sess, decoder_input, op):
    """
    Generates a grid of images by passing a set of numbers to the decoder and getting its output.
    :param sess: Tensorflow Session required to get the decoder output
    :param op: Operation that needs to be called inorder to get the decoder output
    :return: None, displays a matplotlib window with all the merged images.
    """
    x_points = np.arange(0, 1, 1.5).astype(np.float32)
    y_points = np.arange(0, 1, 1.5).astype(np.float32)

    nx, ny = len(x_points), len(y_points)
    plt.subplot()
    gs = gridspec.GridSpec(nx, ny, hspace=0.05, wspace=0.05)

    for i, g in enumerate(gs):
        z = np.concatenate(([x_points[int(i / ny)]], [y_points[int(i % nx)]]))
        z = np.reshape(z, (1, 2))
        x = sess.run(op, feed_dict={decoder_input: z})
        ax = plt.subplot(g)
        img = np.array(x.tolist()).reshape(28, 28)
        ax.imshow(img, cmap='gray')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect('auto')
    plt.show()


def dense(x, n1, n2, name):
    """
    Used to create a dense layer.
    :param x: input tensor to the dense layer
    :param n1: no. of input neurons
    :param n2: no. of output neurons
    :param name: name of the entire dense layer.i.e, variable scope name.
    :return: tensor with shape [batch_size, n2]
    """
    with tf.variable_scope(name, reuse=None):
        weights = tf.get_variable("weights", shape=[n1, n2],
                                  initializer=tf.random_normal_initializer(mean=0., stddev=0.01))
        bias = tf.get_variable("bias", shape=[n2], initializer=tf.constant_initializer(0.0))
        out = tf.add(tf.matmul(x, weights), bias, name='matmul')
        return out


# The autoencoder network
def encoder(x, reuse=False):
    """
    Encode part of the autoencoder
    :param x: input to the autoencoder
    :param reuse: True -> Reuse the encoder variables, False -> Create or search of variables before creating
    :return: tensor which is the hidden latent variable of the autoencoder.
    """
    if reuse:
        tf.get_variable_scope().reuse_variables()
    with tf.name_scope('Encoder'):
        e_dense_1 = tf.nn.relu(dense(x, input_dim, hidden_layer1, 'e_dense_1'))
        e_dense_2 = tf.nn.relu(dense(e_dense_1, hidden_layer1, hidden_layer2, 'e_dense_2'))
        latent_variable = dense(e_dense_2, hidden_layer2, options.z_dim, 'e_latent_variable')
        return latent_variable


def decoder(x, reuse=False):
    """
    Decoder part of the autoencoder
    :param x: input to the decoder
    :param reuse: True -> Reuse the decoder variables, False -> Create or search of variables before creating
    :return: tensor which should ideally be the input given to the encoder.
    """
    if reuse:
        tf.get_variable_scope().reuse_variables()
    with tf.name_scope('Decoder'):
        d_dense_1 = tf.nn.relu(dense(x, options.z_dim, hidden_layer2, 'd_dense_1'))
        d_dense_2 = tf.nn.relu(dense(d_dense_1, hidden_layer2, hidden_layer1, 'd_dense_2'))
        output = tf.nn.sigmoid(dense(d_dense_2, hidden_layer1, input_dim, 'd_output'))
        return output


def train(options):
    """
    Used to train the autoencoder by passing in the necessary inputs.
    :param train_model: True -> Train the model, False -> Load the latest trained model and show the image grid.
    :return: does not return anything
    """
    # Placeholders for input data and the targets
    x_input = tf.placeholder(dtype=tf.float32, shape=[options.batch_size, input_dim], name='Input')
    x_target = tf.placeholder(dtype=tf.float32, shape=[options.batch_size, input_dim], name='Target')
    decoder_input = tf.placeholder(dtype=tf.float32, shape=[1, options.z_dim], name='Decoder_input')

    with tf.variable_scope(tf.get_variable_scope()):
        encoder_output = encoder(x_input)
        decoder_output = decoder(encoder_output)

    with tf.variable_scope(tf.get_variable_scope()):
        decoder_image = decoder(decoder_input, reuse=True)

    # Loss
    loss = tf.reduce_mean(tf.square(x_target - decoder_output))

    # Optimizer
    optimizer = tf.train.AdamOptimizer(learning_rate=options.learning_rate, beta1=options.beta1).minimize(loss)
    init = tf.global_variables_initializer()

    # Visualization
    tf.summary.scalar(name='Loss', tensor=loss)
    tf.summary.histogram(name='Encoder Distribution', values=encoder_output)
    input_images = tf.reshape(x_input, [-1, 28, 28, 1])
    generated_images = tf.reshape(decoder_output, [-1, 28, 28, 1])
    tf.summary.image(name='Input Images', tensor=input_images, max_outputs=10)
    tf.summary.image(name='Generated Images', tensor=generated_images, max_outputs=10)
    summary_op = tf.summary.merge_all()

    # Saving the model
    saver = tf.train.Saver()
    step = 0
    with tf.Session() as sess:
        sess.run(init)
        if not options.run_inference:
            writer = tf.summary.FileWriter(logdir=options.tensorboard_path, graph=sess.graph)
            for i in range(options.epochs):
                n_batches = int(mnist.train.num_examples / options.batch_size)
                for b in range(n_batches):
                    batch_x, _ = mnist.train.next_batch(options.batch_size)
                    sess.run(optimizer, feed_dict={x_input: batch_x, x_target: batch_x})
                    if b % 50 == 0:
                        batch_loss, summary = sess.run([loss, summary_op], feed_dict={x_input: batch_x, x_target: batch_x})
                        writer.add_summary(summary, global_step=step)
                        print("Loss: {}".format(batch_loss))
                        print("Epoch: {}, iteration: {}".format(i, b))
                        with open(options.logs_path + '/log.txt', 'a') as log:
                            log.write("Epoch: {}, iteration: {}\n".format(i, b))
                            log.write("Loss: {}\n".format(batch_loss))
                    step += 1
                saver.save(sess, save_path=options.checkpoints_path, global_step=step)
            print("Model Trained!")
            print("Tensorboard Path: {}".format(options.tensorboard_path))
            print("Log Path: {}".format(options.logs_path + '/log.txt'))
            print("Saved Model Path: {}".format(checkpoints_path))
        else:
            print('Restoring latest saved TensorFlow model...')
            dir_path = os.path.dirname(os.path.realpath(__file__))
            cur_dir = dir_path.split('/')[-1]
            experiments = glob.glob(os.path.join(options.MAIN_PATH, cur_dir) + '/*')
            sorted_experiments = sorted(experiments)
            saver.restore(sess, tf.train.latest_checkpoint(os.path.join(experiments[-1], 'checkpoints')))
            generate_image_grid(sess, decoder_input, op=decoder_image)

if __name__ == '__main__':
    check_tf_version()
    parser = set_config()
    (options, args) = parser.parse_args()
    if not options.run_inference:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        cur_dir = dir_path.split('/')[-1]
        options = extend_options(parser, cur_dir)

    train(options)
