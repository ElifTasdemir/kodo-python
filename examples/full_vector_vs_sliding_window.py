#! /usr/bin/env python
# encoding: utf-8

# Copyright Steinwurf ApS 2011-2013.
# Distributed under the "STEINWURF RESEARCH LICENSE 1.0".
# See accompanying file LICENSE.rst or
# http://www.steinwurf.com/licensing

import os
import random

import kodo


def benchmark(encoder, decoder, channel_condition, data_availablity):
    """Full vector vs sliding window benchmark."""
    # Create some data to encode. In this case we make a buffer
    # with the same size as the encoder's block size (the max.
    # amount a single encoder can encode)
    # Just for fun - fill the input data with random data
    data_in = os.urandom(encoder.block_size())

    # Let's split the data into symbols and feed the encoder one symbol at a
    # time
    symbol_storage = [
        data_in[i:i + encoder.symbol_size()]
        for i in range(0, len(data_in), encoder.symbol_size())
    ]

    results = {}
    ticks = 0
    packet = None
    while not decoder.is_complete():
        ticks += 1
        rank = encoder.rank()
        # Is new data available?
        if rank < encoder.symbols() and random.random() < data_availablity:
            encoder.set_const_symbol(rank, symbol_storage[rank])
            # regardless of the codec we can always send the data systematic
            # rightway.
            packet = encoder.write_payload()
        else:
            got_all_data = (rank == encoder.symbols())
            is_sliding_window = hasattr(encoder, 'read_feedback')
            if got_all_data or is_sliding_window:
                # Encode a packet into the payload buffer
                packet = encoder.write_payload()

        if packet is None:
            continue

        # Send the data to the decoders, here we just for fun
        # simulate that we are loosing 50% of the packets
        if random.random() > channel_condition:
            # Packet got through - pass that packet to the decoder
            decoder.read_payload(packet)

            for symbol_index in range(encoder.symbols()):
                if symbol_index in results:
                    continue
                decoder_symbol = decoder.copy_from_symbol(symbol_index)
                encoder_symbol = symbol_storage[symbol_index]
                # if decoder.is_symbol_uncoded(symbol_index):
                if decoder_symbol == encoder_symbol:
                    results[symbol_index] = ticks

        if not hasattr(encoder, 'read_feedback'):
            continue

        # Transmit the feedback
        feedback = decoder.write_feedback()

        # Simulate loss of feedback
        if random.random() < channel_condition:
            continue

        encoder.read_feedback(feedback)

    # The decoder is complete, now copy the symbols from the decoder
    data_out = decoder.copy_from_symbols()

    # Check we properly decoded the data
    if data_out == data_in:
        return results
    else:
        return None


def main():
    """Main function."""
    # Set the number of symbols (i.e. the generation size in RLNC
    # terminology) and the size of a symbol in bytes
    symbols = 20
    symbol_size = 160

    # In the following we will make an encoder/decoder factory.
    # The factories are used to build actual encoders/decoders
    sliding_window_encoder_factory = kodo.SlidingWindowEncoderFactoryBinary(
        max_symbols=symbols,
        max_symbol_size=symbol_size)

    sliding_window_encoder = sliding_window_encoder_factory.build()

    sliding_window_decoder_factory = kodo.SlidingWindowDecoderFactoryBinary(
        max_symbols=symbols,
        max_symbol_size=symbol_size)

    sliding_window_decoder = sliding_window_decoder_factory.build()

    full_vector_encoder_factory = kodo.FullVectorEncoderFactoryBinary(
        max_symbols=symbols,
        max_symbol_size=symbol_size)

    full_vector_encoder = full_vector_encoder_factory.build()

    full_vector_decoder_factory = kodo.FullVectorDecoderFactoryBinary(
        max_symbols=symbols,
        max_symbol_size=symbol_size)

    full_vector_decoder = full_vector_decoder_factory.build()

    # Set the channel condition
    channel_condition = 0.2
    # Set data availablity
    data_availablity = 0.2

    full_vector_results = benchmark(
        full_vector_encoder, full_vector_decoder, channel_condition,
        data_availablity)

    sliding_window_results = benchmark(
        sliding_window_encoder, sliding_window_decoder, channel_condition,
        data_availablity)

    assert full_vector_results is not None
    assert sliding_window_results is not None

    print("Symbol ID | FullVector | Slidingwindow | Diff")
    for symbol_index in full_vector_results:
        full_vector_result = full_vector_results[symbol_index]
        sliding_window_result = sliding_window_results[symbol_index]
        diff = full_vector_result - sliding_window_result

        print(" {:2}       | {:4}       | {:4}          | {:4}".format(
            symbol_index, full_vector_result, sliding_window_result, diff))


if __name__ == "__main__":
    main()
