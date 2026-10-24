import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.wr_data.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_fifo_push_pop_flags(dut):
    """Verify write, read, occupancy count, and full/empty flags."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    assert dut.empty.value == 1, "FIFO should be empty after reset"
    assert dut.full.value == 0, "FIFO should not be full after reset"

    # Write 16 elements
    depth = 16
    for i in range(depth):
        dut.wr_en.value = 1
        dut.wr_data.value = (i * 7) & 0xFF
        await RisingEdge(dut.clk)

    dut.wr_en.value = 0
    await RisingEdge(dut.clk)

    assert dut.full.value == 1, "FIFO should assert full flag after 16 writes"
    assert dut.empty.value == 0, "FIFO should not be empty"

    # Read and verify FIFO ordering
    dut.rd_en.value = 1
    await RisingEdge(dut.clk)

    for i in range(depth):
        if i == depth - 1:
            dut.rd_en.value = 0  # Deassert on the last cycle to prevent extra read
        await RisingEdge(dut.clk)
        expected = (i * 7) & 0xFF
        assert dut.rd_data.value == expected, f"Data mismatch! Expected: {expected}, got: {dut.rd_data.value}"

    await RisingEdge(dut.clk)
    assert dut.empty.value == 1, "FIFO should be empty after reading all elements"

@cocotb.test
async def test_fifo_sync_rw(dut):
    """Verify synchronous r/w and occupancy count."""
    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    DEPTH = 16
    for i in range(DEPTH - 1):
        dut.wr_en.value = 1
        dut.wr_data.value = (2 * i) & 0xFF
        await RisingEdge(dut.clk)

        dut.wr_data.value = (2 * i + 1) & 0xFF
        await RisingEdge(dut.clk)

        dut.rd_en.value = 1
        dut.wr_en.value = 0
        await RisingEdge(dut.clk)

        # need to wait an additional cycle
        dut.rd_en.value = 0
        await RisingEdge(dut.clk)

        assert dut.rd_data.value == i & 0xFF, f"Data mismatch! Expected: {i & 0xFF}, got: {dut.rd_data.value}"
        assert dut.occupancy.value == i + 1, f"Occupancy mismatch! Expected: {i + 1}, got: {dut.occupancy.value}"
