const http = require('http');

async function getAcess() {

  return new Promise((resolve, reject) => {
    var options = {
      host: 'localhost', //local onde executa a requisição
      port: 80,
      path: '/jwtserver/login'
    };

    http.get(options, function (res) {
      let data = '';

      res.on('data', function (chunk) {
        data += chunk;
      });

      res.on('end', function () {

        try {
          const parsed = JSON.parse(data);
          const token = parsed.token;
          resolve(token);
        } catch (e) {
          console.error("Failed to parse JSON:", e);
        }
      });


    }).on('error', function (e) {
      console.log("Got error: " + e.message);
    });
  });
}

module.exports = {
  getAcess
};