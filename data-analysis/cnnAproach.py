from spectrogram import full_bpm_to_data, HEART_AV_ROOT
from get_heartrates import get_interesting_heartrates
from keras.models import Sequential
from keras.layers.core import Dense, Activation, Dropout, Flatten
from keras.layers.convolutional import Convolution2D, MaxPooling2D
from keras.callbacks import EarlyStopping
from scipy.stats import pearsonr
from math import sqrt
from sklearn.metrics import mean_squared_error
from sklearn.cross_validation import train_test_split
from kbhit import KBHit

import numpy as np
import code
import itertools

kb = KBHit()
(X_train, y_train), (X_test, y_test) = full_bpm_to_data(get_interesting_heartrates(HEART_AV_ROOT))

#so it fits into memory without paging
reduce_to = int(X_train.shape[0] * 0.7)
X_train = X_train[:reduce_to]
y_train = y_train[:reduce_to]

#Y_train = np.array(y_train)
#Y_test = np.array(y_test)
Y_test = y_test
#X_train = np.array(X_train)
#X_test = np.array(X_test)


print(X_train.shape)

def get_model_and_score( X_train, Y_train,
              nb_hidden=50, drop1=0.1, drop2=0.1, drop3=0.5,
              nb_filter=10, nb_pool=2, nb_rows = 2, nb_coloumns = 2):
    model = Sequential()

    model.add(Convolution2D(nb_filter,nb_rows,nb_coloumns, input_shape=(X_train[0].shape)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(nb_pool*2, nb_pool)))

    model.add(Convolution2D(nb_filter,nb_rows // (nb_pool*2),nb_coloumns))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(nb_pool*2, nb_pool)))
    model.add(Dropout(drop1))

    model.add(Convolution2D(nb_filter*2, nb_rows // (nb_pool*2),nb_coloumns))
    model.add(Activation('relu'))

    model.add(MaxPooling2D(pool_size=(nb_pool, nb_pool)))
    model.add(Dropout(drop2))

    model.add(Flatten())
    model.add(Dense(nb_hidden))
    model.add(Activation('relu'))
    model.add(Dropout(drop3))
    model.add(Dense(1))
    model.add(Activation('linear'))

    model.compile(loss='mse', optimizer='adam')

    early_stopping = EarlyStopping(monitor='val_loss', patience=2)
    history = model.fit(X_train, Y_train, batch_size=100, nb_epoch=10,
            verbose=1, validation_split=0.01, callbacks=[early_stopping])

    return history, model

def assess_model(model, X_test, Y_test):
    predictions = model.predict(X_test)
    r = pearsonr(predictions[:,0], Y_test)
    rmse = sqrt(mean_squared_error(predictions, Y_test))
    return r, rmse, predictions


nb_pools = [1,2]
nb_rows = [X_train.shape[2] // 16, 4]
nb_columns = [2, 8]
nb_filters = [5,10]
drop1s = [0,0.1]
drop2s = [0,0.1]
drop3s = [0,0.5]
nb_hiddens = [(5-i)*50 for i in range(2,4)]

print("Model: nb_hiddens, drop1s, drop2s, drop3s, nb_filters, nb_pools, nb_rows, nb_columns")


#X_train, X_validate, Y_train, Y_validate = train_test_split(X_train, Y_train, test_size=0.25, random_state=4)

split_at = X_train.shape[0] // 4

X_validate = np.array(X_train[:split_at])
Y_validate = np.array(y_train[:split_at])
print(split_at)

X_train = np.array(X_train[split_at:])
Y_train = np.array(y_train[split_at:])


prevLoss = 223942309
maxModel = None
stop = False
for args in itertools.product(nb_hiddens, drop1s, drop2s, drop3s, nb_filters, nb_pools, nb_rows, nb_columns):
    print("Model: ", args)
    hist , model = get_model_and_score(X_train, Y_train, *args)
    # most recent loss hist.history["loss"][-1]
    r, rmse, _ = assess_model(model, X_validate, Y_validate)
    print("Model r: ", r)
    print("Model rmse: ", rmse)
    if rmse < prevLoss:
        prevLoss =  rmse
        maxModel = model
    while kb.kbhit():
        if "q" in kb.getch():
            print("quiting due to user pressing q")
            stop = True

    if stop:
        break

del X_train

X_test = np.array(X_test)
Y_test = np.array(Y_test)

r, rmse, _ = assess_model(maxModel, X_test, Y_test)
print("Model r: ", r)
print("Model rmse: ", rmse)
#code.interact(local=locals())
