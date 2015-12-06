from spectrogram import full_bpm_to_data, HEART_AV_ROOT, NormalizedSpectrograms, NormalizedSubjectSplitSpectrograms, getVideoSpectrograms
from get_heartrates import get_interesting_heartrates
from keras.callbacks import EarlyStopping
from kbhit import KBHit

import numpy as np
import code
import random
import learnLib
from numpy.lib.stride_tricks import as_strided as ast

kb = KBHit()

def repeat_n_times(a,n):
    return np.repeat(np.reshape(a,(-1,1,1)),n,axis=1)

#these two functions from: http://www.johnvinyard.com/blog/?p=268
def norm_shape(shape):
    '''
    Normalize numpy array shapes so they're always expressed as a tuple,
    even for one-dimensional shapes.

    Parameters
        shape - an int, or a tuple of ints

    Returns
        a shape tuple
    '''
    try:
        i = int(shape)
        return (i,)
    except TypeError:
        # shape was not a number
        pass

    try:
        t = tuple(shape)
        return t
    except TypeError:
        # shape was not iterable
        pass

    raise TypeError('shape must be an int, or a tuple of ints')
def sliding_window(a,ws,ss = None,flatten = True):
    '''
    Return a sliding window over a in any number of dimensions
    Parameters:
        a  - an n-dimensional numpy array
        ws - an int (a is 1D) or tuple (a is 2D or greater) representing the size
             of each dimension of the window
        ss - an int (a is 1D) or tuple (a is 2D or greater) representing the
             amount to slide the window in each dimension. If not specified, it
             defaults to ws.
        flatten - if True, all slices are flattened, otherwise, there is an
                  extra dimension for each dimension of the input.
    Returns
        an array containing each n-dimensional window from a
    '''

    if None is ss:
        # ss was not provided. the windows will not overlap in any direction.
        ss = ws
    ws = norm_shape(ws)
    ss = norm_shape(ss)

    # convert ws, ss, and a.shape to numpy arrays so that we can do math in every
    # dimension at once.
    ws = np.array(ws)
    ss = np.array(ss)
    shape = np.array(a.shape)


    # ensure that ws, ss, and a.shape all have the same number of dimensions
    ls = [len(shape),len(ws),len(ss)]
    if 1 != len(set(ls)):
        raise ValueError(\
        'a.shape, ws and ss must all have the same length. They were %s' % str(ls))

    # ensure that ws is smaller than a in every dimension
    if np.any(ws > shape):
        raise ValueError(\
        'ws cannot be larger than a in any dimension.\
 a.shape was %s and ws was %s' % (str(a.shape),str(ws)))
    # how many slices will there be in each dimension?
    newshape = norm_shape(((shape - ws) // ss) + 1)
    # the shape of the strided array will be the number of slices in each dimension
    # plus the shape of the window (tuple addition)
    newshape += norm_shape(ws)
    # the strides tuple will be the array's strides multiplied by step size, plus
    # the array's strides (tuple addition)
    newstrides = norm_shape(np.array(a.strides) * ss) + a.strides
    strided = ast(a,shape = newshape,strides = newstrides)
    if not flatten:
        return strided

    # Collapse strided so that it has one more dimension than the window.  I.e.,
    # the new array is a flat list of slices.
    meat = len(ws) if ws.shape else 0
    firstdim = (np.product(newshape[:-meat]),) if ws.shape else ()
    dim = firstdim + (newshape[-meat:])
    return strided.reshape(dim)

def interpolateYs(y, new_dim=30):
    xvals = list(range(1, new_dim + 1))
    n = len(y)
    x = [i*(new_dim / n) for i in range(0, n)]
    return np.reshape(np.interp(xvals, x,y),(-1,1))

#ns = NormalizedSubjectSplitSpectrograms(subjectIdependant=True)#NormalizedSpectrograms()



ns = NormalizedSpectrograms(getVideoSpectrograms())

X_train, Y_train  = ns.getTrainData()
X_train = np.reshape(X_train, (-1,1,1,120))
print(X_train.shape)

#ws = np.array(X_train.shape)
#ss = np.array(X_train.shape)
ws = (1,1,1,30)
ss = (1,1,1,1)
ys = np.array(list(map(lambda x: interpolateYs(x, X_train.shape[-1]), Y_train)))
print(ys.shape)
ys = np.reshape(ys, (-1,1,1,X_train.shape[-1]))
print(ys.shape)
y = sliding_window(ys,ws,ss)
print(y.shape)
Y_train = y[:,:,0,0,0]

X_val, Y_val = ns.getValidationData()
X_val = np.reshape(X_val, (-1,1,1,120))
X_val = sliding_window(X_val,ws,ws)
X_val = X_val[:,0,:,:,:]
Y_val = np.reshape(Y_val, (-1,1))

X_train = sliding_window(X_train,ws,ss)
X_train = X_train[:,0,:,:,:]

#slice the spectrogram
print(X_train.shape)
#Y_train = np.repeat(np.reshape(-1,1), X_train.shape[1], axis=1)
print(Y_train.shape)
print(X_val.shape)
print(Y_val.shape)

learnLib.shuffle_in_unison(X_train, Y_train)

print("Model (nb_filters1, nb_col1, nb_filters2, nb_col2, ltsm_neurons, drop1, drops2)")

prevLoss =  34534645735673
maxModel = None
maxModelOutShape = None
stop = False
models = {}

for args in learnLib.RandomCnnRnnParameters(): #itertools.product(nb_hiddens, drop1s):
    print("Model: ", args)
    model, outshape = learnLib.get_1DCNN_RNN_model(X_train[0].shape, *args)
    print(outshape)
    early_stopping = EarlyStopping(monitor='val_loss', patience=3)
    history = model.fit(X_train, Y_train, batch_size=5000, nb_epoch=20,
           verbose=1, validation_data=(X_val,Y_val), callbacks=[early_stopping])


    # most recent loss hist.history["loss"][-1]
    r, rmse, _ = learnLib.assess_model(model, X_val, Y_val)
    models[args]  = r,rmse
    print("Model r: ", r)
    print("Model rmse: ", rmse)
    if rmse < prevLoss:
        prevLoss = rmse
        maxModel = model
        maxModelOutShape = outshape
    while kb.kbhit():
        try:
            if "q" in kb.getch():
                print("quiting due to user pressing q")
                stop = True
        except UnicodeDecodeError:
            pass

    if stop:
        break


X_test, Y_t = ns.getTestData()

X_test = np.reshape(X_test, (-1,1,1,120))
X_test = sliding_window(X_test,ws,ws)
X_test = X_test[:,0,:,:,:]
Y_test = np.reshape(Y_t, (-1,1))


learnLib.printModels(models)

r, rmse, preds = learnLib.assess_model(maxModel, X_test, Y_test)
predicted_bpm = np.array(list(map(ns.unnormalize_bpm, preds)))
print("Model r: ", r)
print("Model rmse: ", rmse)
code.interact(local=locals())
