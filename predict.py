import sys
import tensorflow as tf
import numpy as np
import train
import config
import data_processer


def get_prediction(session, model, enc_vocab, rev_dec_vocab, text):
    token_ids = data_processer.sentence_to_token_ids(text, enc_vocab)
    bucket_id = min([b for b in range(len(config.buckets))
                     if config.buckets[b][0] > len(token_ids)])
    encoder_inputs, decoder_inputs, target_weights = model.get_batch({bucket_id: [(token_ids, [])]}, bucket_id)

    _, _, output_logits = model.step(session, encoder_inputs, decoder_inputs,
                                     target_weights, bucket_id, True, beam_search=False)

    outputs = [int(np.argmax(logit, axis=1)) for logit in output_logits]
    if data_processer.EOS_ID in outputs:
        outputs = outputs[:outputs.index(data_processer.EOS_ID)]
    text = "".join([tf.compat.as_str(rev_dec_vocab[output]) for output in outputs])
    return text

#    normal_prediction(bucket_id, decoder_inputs, encoder_inputs, model, rev_dec_vocab, session, target_weights)

    #if config.beam_search:
#        beam_search_prediction(bucket_id, decoder_inputs, encoder_inputs, model, rev_dec_vocab, session,
#                               target_weights)

#def normal_prediction(bucket_id, decoder_inputs, encoder_inputs, model, rev_dec_vocab, session, target_weights):
#    _, _, output_logits = model.step(session, encoder_inputs, decoder_inputs,
#                                     target_weights, bucket_id, True, beam_search=False)
#    outputs = [int(np.argmax(logit, axis=1)) for logit in output_logits]
#    if data_processer.EOS_ID in outputs:
#        outputs = outputs[:outputs.index(data_processer.EOS_ID)]
#    text = "".join([tf.compat.as_str(rev_dec_vocab[output]) for output in outputs])
#    print("Normal Prediction")
#    print(text)


def get_beam_serch_prediction(session, model, enc_vocab, rev_dec_vocab, text):
    token_ids = data_processer.sentence_to_token_ids(text, enc_vocab)
    bucket_id = min([b for b in range(len(config.buckets))
                     if config.buckets[b][0] > len(token_ids)])
    encoder_inputs, decoder_inputs, target_weights = model.get_batch({bucket_id: [(token_ids, [])]}, bucket_id)

    path, symbol, output_logits = model.step(session, encoder_inputs, decoder_inputs,
                                             target_weights, bucket_id, True, beam_search=config.beam_search)
    beam_size = config.beam_size
    k = output_logits[0]
    paths = []
    for kk in range(beam_size):
        paths.append([])
    curr = list(range(beam_size))
    num_steps = len(path)
    for i in range(num_steps - 1, -1, -1):
        for kk in range(beam_size):
            paths[kk].append(symbol[i][curr[kk]])
            curr[kk] = path[i][curr[kk]]
    recos = set()
    ret = []
    i = 0
    for kk in range(beam_size):
        foutputs = [int(logit) for logit in paths[kk][::-1]]

        # If there is an EOS symbol in outputs, cut them at that point.
        if data_processer.EOS_ID in foutputs:
            #         # print outputs
            foutputs = foutputs[:foutputs.index(data_processer.EOS_ID)]
        rec = " ".join([tf.compat.as_str(rev_dec_vocab[output]) for output in foutputs])
        if rec not in recos:
            recos.add(rec)
#            print("reply {}".format(i))
#            i = i + 1
            ret.append(rec)
    return ret

def predict():
    # Only allocate part of the gpu memory when predicting.
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.2)
    tf_config = tf.ConfigProto(gpu_options=gpu_options)

    with tf.Session(config=tf_config) as sess:

        train.show_progress("Creating model...")
        model = train.create_or_restore_model(sess, config.buckets, forward_only=True, beam_search=config.beam_search, beam_size=40)
        model.batch_size = 1
        train.show_progress("done\n")

        enc_vocab, _ = data_processer.initialize_vocabulary(config.VOCAB_ENC_TXT)
        _, rev_dec_vocab = data_processer.initialize_vocabulary(config.VOCAB_DEC_TXT)

        sys.stdout.write("> ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        while line:
            if config.beam_search:
                print("beam")
                replies = get_beam_serch_prediction(sess, model, enc_vocab, rev_dec_vocab, line)
                for i, text in enumerate(replies):
                    print(i, text)
            else:
                print("normal")
                predicted = get_prediction(sess, model, enc_vocab, rev_dec_vocab, line)
                print(predicted)
            print("> ", end="")
            sys.stdout.flush()
            line = sys.stdin.readline()

if __name__ == '__main__':
    predict()
