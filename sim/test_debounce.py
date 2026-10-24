import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.sig_in.value = 0
    await Timer(100, unit="ns")
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_debouncer_glitch_and_stable(dut):
    """Test contact bounce rejection and edge pulse generation."""
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # 1. Check initial state
    assert dut.sig_debounced.value == 0, "Error: sig_debounced is not 0 after reset"

    # 2. Generate short glitch pulses
    for _ in range(5):
        dut.sig_in.value = 1
        await Timer(50, unit="ns")
        dut.sig_in.value = 0
        await Timer(50, unit="ns")

    assert dut.sig_debounced.value == 0, "Error: glitch noise changed sig_debounced!"
    assert dut.edge_rise.value == 0, "Error: false edge_rise pulse during glitch noise!"

    # 3. Apply stable high input (exceeding STABLE_TIME)
    dut.sig_in.value = 1
    # Wait for propagation
    rise_detected = False
    for _ in range(600_000):
        await RisingEdge(dut.clk)
        if dut.edge_rise.value == 1:
            assert not rise_detected, "Error: edge_rise occurred more than once!"
            rise_detected = True
        if dut.sig_debounced.value == 1 and rise_detected:
            break

    assert rise_detected, "Error: 1-cycle edge_rise pulse not detected!"
    assert dut.sig_debounced.value == 1, "Error: sig_debounced did not transition to high!"

    await RisingEdge(dut.clk)
    rise_detected = dut.edge_rise.value == 1
    assert not rise_detected, "Error: edge_rise should be a 1-cycle pulse!"

    # 4. Check for edge_fall
    dut.sig_in.value = 0
    fall_detected = False
    for _ in range(5):
        await RisingEdge(dut.clk)
        if dut.edge_fall.value == 1:
            assert not fall_detected, "Error: edge_fall occurred more than once!"
            fall_detected = True
        if dut.sig_debounced.value == 0 and fall_detected:
            break

    assert fall_detected, "Error: 1-cycle edge_fall pulse not detected!"
    assert dut.sig_debounced.value == 0, "Error: sig_debounced did not transition to low!"

    await RisingEdge(dut.clk)
    fall_detected = dut.edge_fall.value == 1
    assert not fall_detected, "Error: edge_fall should be a 1-cycle pulse!"

@cocotb.test()
async def test_debouncer_counter_overflow(dut):
    """Test whether the counter overflows."""
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.sig_in.value = 1

    STABLE_TIME = 500_000
    MAX_CYCLES = 2 ** (STABLE_TIME + 1).bit_length()

    rise_detected = False
    for _ in range(STABLE_TIME + 100):
        await RisingEdge(dut.clk)
        if dut.edge_rise.value == 1:
            rise_detected = True
            break

    assert rise_detected, "Error: 1-cycle edge_rise pulse not detected!"

    # The counter is now equal to STABLE_TIME.
    # Assuming that the debouncer uses an optimal number of bits for the
    # counter, which is at most $clog2(STABLE_TIME + 2)), the counter
    # will overflow and get back to STABLE_TIME after another MAX_CYCLES cycles
    # if there are no mitigations. In such case, edge_rise will occur more than
    # # once.
    for _ in range(MAX_CYCLES):
        await RisingEdge(dut.clk)
        if dut.edge_rise.value == 1:
            assert not rise_detected, "Error: edge_rise occurred more than once!"
