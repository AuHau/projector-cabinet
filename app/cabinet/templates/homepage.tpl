{% args config, messages %}

<html lang="en">
<head>
    <title>Projector cabinet!</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-aFq/bzH65dt+w6FI2ooMVUpc+21e0SRygnTpmBvdBgSdnuTN7QbdgL+OapgHtvPp" crossorigin="anonymous">
</head>
<body>
<div class="container">
    <div class="row">
        <div class="col-md-8 offset-md-2">

            <h1 class="mb-4 mt-8">Projector's cabinet!</h1>

            {% for msg in messages %}
                <div class="alert alert-{{ msg[0] }}" role="alert">
                    {{ msg[1] }}
                </div>
            {% endfor %}

            <form>
                <div class="d-grid gap-2">
                    <input type="hidden" name="go" value="1">
                    <button class="btn btn-primary" type="submit">Trigger cabinet</button>
                </div>
            </form>

            <form>
                <div class="d-grid gap-2">
                    <input type="hidden" name="reboot" value="1">
                    <button class="btn btn-danger" type="submit">Reboot</button>
                </div>
            </form>




            <h2  class="mt-2">Configuration</h2>
            <form method="post">
                {% for config_key in dir(config) %}
                    {% if not config_key.startswith('_') %}
                        <div class="mb-3">
                            <label for="{{ config_key }}" class="form-label">{{ config_key[0].upper() + config_key.replace("_", " ")[1:] }}</label>
                            <input name="{{ config_key }}" type="text" class="form-control" id="{{ config_key }}" value="{{ getattr(config, config_key) }}">
                        </div>
                    {% endif %}
                {% endfor %}
                <button type="submit" class="btn btn-primary">Update</button>
            </form>
        </div>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha2/dist/js/bootstrap.bundle.min.js" integrity="sha384-qKXV1j0HvMUeCBQ+QVp7JcfGl760yU08IQ+GpUo5hlbpg51QRiuqHAJz8+BrxE/N" crossorigin="anonymous"></script>
</body>
</html>
