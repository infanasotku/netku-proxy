proto/xray.proto:
	mkdir -p proto
	curl -L -o proto/xray.proto https://raw.githubusercontent.com/infanasotku/netku/master/proto/xray.proto

generate: proto/xray.proto
	python -m grpc_tools.protoc -Iapp/infra/grpc/gen=proto/ \
	--python_out=. \
	--grpc_python_out=. \
	--pyi_out=. \
	proto/xray.proto
	ruff check --fix app/infra/grpc/gen 
