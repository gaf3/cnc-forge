window.DRApp = new DoTRoute.Application();

DRApp.load = function (name) {
    return $.ajax({url: name + ".html", async: false}).responseText;
}

$.ajaxPrefilter(function(options, originalOptions, jqXHR) {});

DRApp.controller("Base",null,{
    rest: function(type,url,data) {
        var response = $.ajax({
            type: type,
            url: url,
            contentType: "application/json",
            data: data ? JSON.stringify(data) : (type != 'GET' ? '{}' : null),
            dataType: "json",
            async: false
        });
        if ((response.status != 200) && (response.status != 201) && (response.status != 202)) {
            alert(type + ": " + url + " failed");
            throw (type + ": " + url + " failed");
        }
        return response.responseJSON;
    },
    forge_list: function() {
        this.it = this.rest("GET", "api/forge");
        this.application.render(this.it);
    },
    forge_retrieve: function() {
        this.it = this.rest("GET", "api/forge/" + DRApp.current.path.id);
        this.application.render(this.it);
    },
    delay_timer: null,
    delay_clear: function() {
        if (this.delay_timer) {
            window.clearTimeout(this.delay_timer);
        }
    },
    delay_change: function() {
        this.delay_clear();
        this.delay_timer = window.setTimeout($.proxy(this, "fields_change"), 2000);
    },
    fields_change: function() {
        this.delay_clear();
        this.it = this.rest("OPTIONS", "api/cnc/" + DRApp.current.path.id, this.fields_request());
        this.application.render(this.it);
    },
    field_value: function(field, value, values) {
        for (var option = 0; option < field.options.length; option++) {
            if (value == field.options[option]) {
                if (Array.isArray(values)) {
                    values.push(field.options[option]);
                } else {
                    values[field.name] = field.options[option];
                }
            }
        }
    },
    fields_values: function(prefix, fields) {
        prefix = prefix || [];
        fields = fields || this.it.fields;
        var values = {};
        for (var index = 0; index < fields.length; index++) {
            var field = fields[index];
            if (field.fields) {
                values[field.name] = this.fields_values(prefix.concat(field.name), field.fields);
                continue;
            }
            var full_name = prefix.concat(field.name).join('-').replace(/\./g, '-');
            if (field.readonly) {
                continue
            } else if (field.options && field.style != "select") {
                if (field.multi) {
                    values[field.name] = [];
                    var that = this;
                    $("input[name='" + full_name + "']:checked").each(function () {
                        that.field_value(field, $(this).val(), values[field.name]);
                    });
                } else {
                    this.field_value(field, $("input[name='" + full_name+ "']:checked").val(), values);
                }
            } else if (field.bool) {
                values[field.name] = $('#' + full_name).is(":checked");
            } else {
                values[field.name] = $('#' + full_name).val();
            }
            if (field.name == "yaml" && values[field.name] == "") {
                values[field.name] = "{}";
            }
        }
        return values;
    },
    fields_request: function() {
        var request = {};
        request['values'] = this.fields_values();
        return request;
    },
    create: function() {
        this.it = this.rest("OPTIONS", "api/cnc/" + DRApp.current.path.id);
        this.application.render(this.it);
    },
    create_save: function(action) {
        var request = this.fields_request();
        request['action'] = action;
        this.it = this.rest("OPTIONS", "api/cnc/" + DRApp.current.path.id, request);
        if (this.it.errors && this.it.errors.length) {
            this.application.render(this.it);
        } else {
            this.application.go("cnc_retrieve", this.rest("POST", "api/cnc/" + DRApp.current.path.id, request).cnc.id);
        }
    },
    cnc_timer: null,
    cnc_clear: function() {
        if (this.cnc_timer) {
            window.clearTimeout(this.cnc_timer);
        }
    },
    cnc_refresh: function() {
        this.cnc_clear();
        this.cnc_retrieve();
    },
    cnc_list: function() {
        this.it = this.rest("GET", "api/cnc");
        this.application.render(this.it);
    },
    cnc_retrieve: function() {
        var previous = this.it;
        this.it = this.rest("GET", "api/cnc/" + DRApp.current.path.id);
        if (previous.yaml != this.it.yaml) {
            this.application.render(this.it);
        }
        this.cnc_timer = window.setTimeout($.proxy(this, "cnc_refresh"), 5000);
    },
    cnc_retry: function() {
        this.it = this.rest("PATCH", "api/cnc/" + DRApp.current.path.id);
        this.application.render(this.it);
    },
    cnc_edit: function() {
        this.it = this.rest("PATCH", "api/cnc/" + DRApp.current.path.id, {save: false});
        this.application.render(this.it);
    },
    cnc_save: function() {
        var yaml = $("#yaml").val();
        this.rest("PATCH", "api/cnc/" + DRApp.current.path.id, {yaml: yaml});
        this.application.go("cnc_retrieve", DRApp.current.path.id);
    },
    cnc_cancel: function() {
        this.application.go("cnc_retrieve", DRApp.current.path.id);
    },
    cnc_delete: function() {
        this.it = this.rest("DELETE", "api/cnc/" + DRApp.current.path.id);
        this.application.go("cnc_list");
    }
});

// Service

DRApp.partial("Header", DRApp.load("header"));
DRApp.partial("Form", DRApp.load("form"));
DRApp.partial("Footer", DRApp.load("footer"));

DRApp.template("Home", DRApp.load("home"), null, DRApp.partials);
DRApp.template("Fields", DRApp.load("fields"), null, DRApp.partials);
DRApp.template("Forges", DRApp.load("forges"), null, DRApp.partials);
DRApp.template("Forge", DRApp.load("forge"), null, DRApp.partials);
DRApp.template("Create", DRApp.load("create"), null, DRApp.partials);
DRApp.template("CnCs", DRApp.load("cncs"), null, DRApp.partials);
DRApp.template("CnC", DRApp.load("cnc"), null, DRApp.partials);
DRApp.template("Edit", DRApp.load("edit"), null, DRApp.partials);

DRApp.route("home", "/", "Home", "Base");
DRApp.route("forge_list", "/forge", "Forges", "Base", "forge_list");
DRApp.route("forge_retrieve", "/forge/{id:^.+$}", "Forge", "Base", "forge_retrieve");
DRApp.route("create", "/cnc/{id:^.+$}/create", "Create", "Base", "create");
DRApp.route("cnc_list", "/cnc", "CnCs", "Base", "cnc_list");
DRApp.route("cnc_retrieve", "/cnc/{id:^.+$}", "CnC", "Base", "cnc_retrieve", "cnc_clear");
DRApp.route("cnc_edit", "/cnc/{id:^.+$}/edit", "Edit", "Base", "cnc_edit");
