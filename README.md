# Crush me back!

Be notified when your crush crushed you back

## Installation

To install the project, follow these steps:

1. Clone the repository with
```bash
 git clone https://github.com/afranck64/crush-me-back
```
2. Install the project dependencies: [docker](https://docs.docker.com/get-docker/) and [docker-compose](https://docs.docker.com/compose/install/)
3. Set up environment variables in a `.env` file in the project root folder based on the template `.env.template`
4. [Optional] Set up a logging configuration in a `web/log.conf` file based on the template `web/log.conf.template`. The template can be used `as is`
5. Start the server in dev mode
```bash
docker-compose run web_dev
```

## Usage

To run the project use the following command:

```bash
docker-compose run web
```
the project will listen to requests send to the socket file `sockets/web.socket`

To run the project in dev mode use following command:
```bash
docker-compose run web_dev
```
The application will accessible at http://localhost:5000/.

## Tests

To run tests, run the following command:
```bash
docker-compose run test
```

## Contributing

Contributions are welcome! To contribute, follow these steps:

1. Fork the repository.
2. Create a branch for your contribution with `git checkout -b my_new_feature`.
3. Make your changes.
4. Submit a pull request on main branch.

## License

This project is licensed under the MIT License.

