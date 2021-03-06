#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# ==============================================================================
#          \file   torch-train.py
#        \author   chenghuige  
#          \date   2019-08-02 01:05:59.741965
#   \Description  
# ==============================================================================

  
from __future__ import absolute_import, division, print_function

import multiprocessing
import os
import sys

import gezi
import melt

import tensorflow as tf

import evaluate as ev

import lele
import loss

import pyt.model as base
import torch
import text_dataset
from pyt.dataset import get_dataset
from pyt.model import *
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader

flags = tf.app.flags
FLAGS = flags.FLAGS

logging = melt.logging

import horovod.torch as hvd
hvd.init()
torch.cuda.set_device(hvd.local_rank())

def main(_):
  FLAGS.torch_only = True
  melt.init()
  fit = melt.get_fit()

  FLAGS.eval_batch_size = 512 * FLAGS.valid_multiplier

  model_name = FLAGS.model
  model = getattr(base, model_name)() 

  model = model.cuda()

  loss_fn = nn.BCEWithLogitsLoss()

  td = text_dataset.Dataset()

  train_files = gezi.list_files('../input/train/*')
  train_ds = get_dataset(train_files, td)
  
  #kwargs = {'num_workers': 4, 'pin_memory': True, 'collate_fn': lele.DictPadCollate()}
  #kwargs = {'num_workers': 0, 'pin_memory': True, 'collate_fn': lele.DictPadCollate()}
  #kwargs = {'num_workers': 4, 'pin_memory': True, 'collate_fn': lele.DictPadCollate()}
  
  num_workers = 1
  kwargs = {'num_workers': num_workers, 'pin_memory': False, 'collate_fn': lele.DictPadCollate()}

  train_sampler = train_ds
  train_sampler = torch.utils.data.distributed.DistributedSampler(
    train_ds, num_replicas=hvd.size(), rank=hvd.rank())
  
  train_dl = DataLoader(train_ds, FLAGS.batch_size, sampler=train_sampler, **kwargs)
  
  valid_files = gezi.list_files('../input/valid/*')
  valid_ds = get_dataset(valid_files, td)

  kwargs['num_workers'] = 1
  # support shuffle=False from version 1.2
  valid_sampler = torch.utils.data.distributed.DistributedSampler(
      valid_ds, num_replicas=hvd.size(), rank=hvd.rank(), shuffle=False)

  kwargs['num_workers'] = 1
  valid_sampler2 = torch.utils.data.distributed.DistributedSampler(
      valid_ds, num_replicas=hvd.size(), rank=hvd.rank(), shuffle=False)
  
  valid_dl = DataLoader(valid_ds, FLAGS.eval_batch_size, sampler=valid_sampler, **kwargs)
  valid_dl2 = DataLoader(valid_ds, FLAGS.batch_size, sampler=valid_sampler2, **kwargs)

  fit(model,  
      loss_fn,
      dataset=train_dl,
      valid_dataset=valid_dl,
      valid_dataset2=valid_dl2,
      eval_fn=ev.evaluate,
      valid_write_fn=ev.valid_write,
      #write_valid=FLAGS.write_valid)   
      write_valid=False,
     )


if __name__ == '__main__':
  tf.app.run()  
