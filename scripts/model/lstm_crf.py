import torch
import torch.nn as nn
from torchcrf import CRF
import sys
sys.path.append('..')
from utils import get_variable
from model.char_cnn import CharCNN


class LSTMCRFTagger(nn.Module):
    def __init__(self, vocab_dim, tag_dim, embed_dim=300, hidden_dim=1000, batch_size=32, num_layers=1, use_gpu=True, alphabet_size=50):
        super().__init__()
        self.alphabet_size = alphabet_size
        self.char_embedding_dim = 200
        self.char_hidden_dim =  1000
        self.char_dropout = 0.5

        self.batch_size = batch_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.tag_dim = tag_dim
        self.num_layers = num_layers
        self.use_gpu = use_gpu
        
        self.embed = nn.Embedding(vocab_dim, embed_dim) 
        self.char_cnn = CharCNN(self.alphabet_size, self.char_embedding_dim, self.hidden_dim, dropout=self.char_dropout, gpu=use_gpu)
        self.lstm = nn.LSTM(embed_dim + self.char_hidden_dim, hidden_dim // 2, num_layers=1, bidirectional=True)
        self.hidden = self.init_hidden()
        self.hidden2tag = nn.Linear(hidden_dim, tag_dim)
        self.crf = CRF(self.tag_dim)

    def init_hidden(self):
        return (get_variable(torch.zeros(2 * self.num_layers, self.batch_size, self.hidden_dim // 2), use_gpu=self.use_gpu),
                get_variable(torch.zeros(2 * self.num_layers, self.batch_size, self.hidden_dim // 2), use_gpu=self.use_gpu))

    def loss(self, x, char_x, y):
        mask = get_variable(torch.autograd.Variable(x.data.gt(0)), use_gpu=self.use_gpu)
        self.hidden = self.init_hidden()
        char_hidden = self.char_cnn(char_x)
        print('char_hidden: {}'.format(char_hidden.shape))
        embeds = self.embed(x)
        print('embeds_hidden: {}'.format(embeds.shape))
        char_word_tensor = torch.cat([embeds, char_hidden], dim=2)
        print('char_word_tensor: {}'.format(char_word_tensor.shape))
        lstm_out, self.hidden = self.lstm(char_word_tensor, self.hidden)
        #print('lstm_out_size: {}'.format(lstm_out.size()))
        lstm_feats = self.hidden2tag(lstm_out)
        #print('lstm_feats: {}'.format(lstm_feats.size()))
        log_likelihood = self.crf(lstm_feats, y, mask=mask)
        # log_likelihoodを最大にすれば良いが、最小化するので-1をかけている。
        return -1 * log_likelihood

    def forward(self, x):
        self.hidden = self.init_hidden()
        embeds = self.embed(x)
        #print('\nembed_size: {}'.format(embeds.size()))
        lstm_out, self.hidden = self.lstm(embeds, self.hidden)
        #print('lstm_out_size: {}'.format(lstm_out.size()))
        lstm_feats = self.hidden2tag(lstm_out)
        #print('lstm_feats: {}'.format(lstm_feats.size()))
        decoded = torch.FloatTensor(self.crf.decode(lstm_feats))
        #print('decoded: {}'.format(decoded.shape))
        return decoded
