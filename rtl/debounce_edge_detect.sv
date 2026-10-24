`timescale 1ns / 1ps

module debounce_edge_detect #(
    parameter int unsigned CLK_FREQ_HZ    = 50_000_000,
    parameter int unsigned STABLE_TIME_MS = 10
) (
    input  logic clk,
    input  logic rst_n,
    input  logic sig_in,
    output logic sig_debounced,
    output logic edge_rise,
    output logic edge_fall
);

    // The counter counts up to CYCLES + 1. he moment it gets to CYCLES, the
    // input signal is deemed stable and edge_rise is set. At CYCLES + 1
    // edge_rise is unset and the counter is stopped to prevent overflow.
    // The interval [0, CYCLES + 1] has CYCLES + 2 integers.
    parameter int unsigned CYCLES = (CLK_FREQ_HZ * STABLE_TIME_MS) / 1000;
    parameter int unsigned CYCLES_BITS = $clog2(CYCLES + 2);

    logic sig_d, sig_sync;
    logic [CYCLES_BITS-1:0] counter;

    // Synchronize the input
    // i'm not entirely sure if a third register should be used, right between
    // the synchronizer's output and counter's input
    // directly comparing sig_d != sig_sync to determine whether the input has
    // changed is probably risky since sig_d might be metastable, but what do i know
    always_ff @(posedge clk) begin
        sig_d <= sig_in;
        sig_sync <= sig_d;
    end

    // i reckon checking these two for equality is better than checking twice
    // for inequality, sth like counter < CYCLES
    logic finished_now, finished_before;
    assign finished_now = counter == CYCLES;
    assign finished_before = counter == CYCLES + 1;

    // reset is active-low, synchronous and handled as if the input has changed,
    // for example it emits edge_fall
    // is this okay?
    logic changed_now;
    assign changed_now = !rst_n || sig_d != sig_sync;

    always_ff @(posedge clk) begin
        if (changed_now) counter <= '0;
        else if (!finished_before) counter <= counter + 1'b1; 
    end

    assign edge_rise = finished_now;
    assign edge_fall = finished_before & changed_now;
    assign sig_debounced = (finished_now || finished_before) & sig_sync;

endmodule
