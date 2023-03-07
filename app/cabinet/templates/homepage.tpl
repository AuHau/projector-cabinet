{% args data %}

<html lang="en">
<head>
    <title>Projector cabinet!</title>
</head>
<body>
<h1>Projector cabinet!</h1>

{% if "message" in data %}
    <p>
        <strong>{{ data["message"] }}</strong>
        <br><br>
    </p>
{% endif %}
<form method="post">
    <fieldset>
        <legend>Target</legend>
        Current actuator's target: <input name="target" type="number" value="{{ data["current_target"] }}" min="0"
                                          max="200">mm
        <input type="submit" value="Update target">
    </fieldset>
</form>
<form method="post">
    <input type="hidden" name="go" value="1">
    <button type="submit">LETS GOOOO!</button>
</form>
</body>
</html>
