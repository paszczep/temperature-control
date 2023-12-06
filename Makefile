go:
	docker run -p 9000:8080 -t temp_ctrl_lambda
build:
	docker build -t temp_ctrl_lambda .
