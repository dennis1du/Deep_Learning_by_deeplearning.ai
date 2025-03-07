import numpy as np
import tensorflow as tf
import tensorflow.keras.backend as K

import random
from faker import Faker
from tqdm import tqdm
from babel.dates import format_date

import matplotlib.pyplot as plt

# random seeds
Faker.seed(12345)
random.seed(12345)

# Define format of the data we would like to generate
FORMATS = ['short',
           'medium',
           'long',
           'full',
           'full',
           'full',
           'full',
           'full',
           'full',
           'full',
           'full',
           'full',
           'full',
           'd MMM YYY', 
           'd MMMM YYY',
           'dd MMM YYY',
           'd MMM, YYY',
           'd MMMM, YYY',
           'dd, MMM YYY',
           'd MM YY',
           'd MMMM YYY',
           'MMMM d YYY',
           'MMMM d, YYY',
           'dd.MM.YY']

# change this if you want it to work with another language
LOCALES = ['en_US']

def load_date():
    '''
    Load some fake dates.
    
    Returns:
    tuple containing human readable string (e.g. "9 may 1998"), machine readable string (e.g. "1998-05-09"), and data object
    '''
    fake = Faker()
    dt = fake.date_object()
    
    try:
        human_readable = format_date(dt, format=random.choice(FORMATS), locale='en_US')  # locale=random.choice(LOCALES)
        human_readable = human_readable.lower()
        human_readable = human_readable.replace(',', '')
        machin_readable = dt.isoformat()
    
    except AttributeError:
        return None, None, None
    
    return human_readable, machin_readable, dt

def load_dataset(m):
    '''
    Load dataset with m examples and vocabularies
    '''
    
    human_vocab = set()
    machine_vocab = set()
    dataset = []

    for _ in tqdm(range(m)):
        h, m, _ = load_date()
        if h is not None:
            dataset.append((h, m))
            human_vocab.update(tuple(h))
            machine_vocab.update(tuple(m))
    
    human = dict(zip(sorted(human_vocab) + ['<unk>', '<pad>'], list(range(len(human_vocab) + 2))))
    inv_machine = dict(enumerate(sorted(machine_vocab)))
    machine = {v:k for k, v in inv_machine.items()}
    
    return dataset, human, machine, inv_machine

def str_to_int(string, length, vocab):
    '''
    Convert all strings in the vocabulary into a list of integers representing the positions of the input string's character in the "vocab"
    
    Arguments:
        --string: input string, e.g. 'Wed 10 Jul 2007'
        --length: the number of total time-steps, determines if the output will be padded or cut
        --vocab: vocabulary, dictionary used to index every character of the input string
    
    Returns:
    rep: list of integers (or '<unk>') of size=length, representing the position of the string's character int the vocabulary
    
    '''
    
    string = string.lower()
    string = string.replace(',', '')
    
    if len(string) > length:
        string = string[:length]
    
    rep = list(map(lambda x: vocab.get(x, '<unk>'), string))
    
    if len(string) < length:
        rep += [vocab['<pad>']] * (length - len(string))
    
    return rep

def int_to_str(ints, inv_vocab):
    '''
    Output a machine readable list of characters based on a list of indices in the machine's vocabulary
    
    Arguments:
        --ints: list of integers, representing indices in the machine's vocabulary
        --inv_vocab: dictionary mapping machine readable indices to machine readable characters
    
    Returns:
    l: list of characters corresponding to the indices of ints from inv_vocab mapping
    '''
    
    l = [inv_vocab[i] for i in ints]
    return l

def preprocess_data(dataset, human_vocab, machine_vocab, Tx, Ty):
    
    X, y = zip(*dataset)
    X = np.array([str_to_int(x, Tx, human_vocab) for x in X])
    y = np.array([str_to_int(t, Ty, machine_vocab) for t in y])
    
    X_1h = np.array(list(map(lambda x: tf.keras.utils.to_categorical(x, num_classes=len(human_vocab)), X)))
    y_1h = np.array(list(map(lambda x: tf.keras.utils.to_categorical(x, num_classes=len(machine_vocab)), y)))
    
    return X, y, X_1h, y_1h

def plot_attention_map(model, input_vocabulary, inv_output_vocabulary, text, n_s = 128, num = 6, Tx = 30, Ty = 10):
    """
    Plot the attention map.
  
    """
    attention_map = np.zeros((10, 30))
    Ty, Tx = attention_map.shape
    
    s0 = np.zeros((1, n_s))
    c0 = np.zeros((1, n_s))
    layer = model.layers[num]

    encoded = np.array(str_to_int(text, Tx, input_vocabulary)).reshape((1, 30))
    encoded = np.array(list(map(lambda x: tf.keras.utils.to_categorical(x, num_classes=len(input_vocabulary)), encoded)))

    f = K.function(model.inputs, [layer.get_output_at(t) for t in range(Ty)])
    r = f([encoded, s0, c0])
    
    for t in range(Ty):
        for t_prime in range(Tx):
            attention_map[t][t_prime] = r[t][0,t_prime,0]

    # Normalize attention map
#     row_max = attention_map.max(axis=1)
#     attention_map = attention_map / row_max[:, None]

    prediction = model.predict([encoded, s0, c0])
    
    predicted_text = []
    for i in range(len(prediction)):
        predicted_text.append(int(np.argmax(prediction[i], axis=1)))
        
    predicted_text = list(predicted_text)
    predicted_text = int_to_str(predicted_text, inv_output_vocabulary)
    text_ = list(text)
    
    # get the lengths of the string
    input_length = len(text)
    output_length = Ty
    
    # Plot the attention_map
    plt.clf()
    f = plt.figure(figsize=(8, 8.5))
    ax = f.add_subplot(1, 1, 1)

    # add image
    i = ax.imshow(attention_map, interpolation='nearest', cmap='Blues')

    # add colorbar
    cbaxes = f.add_axes([0.2, 0, 0.6, 0.03])
    cbar = f.colorbar(i, cax=cbaxes, orientation='horizontal')
    cbar.ax.set_xlabel('Alpha value (Probability output of the "softmax")', labelpad=2)

    # add labels
    ax.set_yticks(range(output_length))
    ax.set_yticklabels(predicted_text[:output_length])

    ax.set_xticks(range(input_length))
    ax.set_xticklabels(text_[:input_length], rotation=45)

    ax.set_xlabel('Input Sequence')
    ax.set_ylabel('Output Sequence')

    # add grid and legend
    ax.grid()

    #f.show()
    
    return attention_map