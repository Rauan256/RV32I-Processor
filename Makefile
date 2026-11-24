.PHONY: gen ref rtl vivado clean

gen:
	python3 tests/gen_tests.py

ref: gen
	python3 tools/ref_model.py

rtl:
	python3 scripts/run_verilator.py

vivado:
	vivado -mode batch -source vivado/run_ooc.tcl

clean:
	rm -rf obj_dir
