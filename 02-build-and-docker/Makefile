all:
	make -C lib
	make -C apps/backend
	make -C apps/balancer
	make -C apps/loadgen

clean:
	make -C apps/backend clean
	make -C apps/balancer clean
	make -C apps/loadgen clean
	make -C lib clean
