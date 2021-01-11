var DoTRoute = {};

// Exception

DoTRoute.Exception = function(message) {
    
    this.name = "DoTRoute.Exception";
    this.message = message;

}

DoTRoute.Exception.prototype = Object.create(Error.prototype);
DoTRoute.Exception.prototype.constructor = DoTRoute.Exception;

// Controller

DoTRoute.Controller = function(application,name,base,actions) {

    // Overlay if there's a base

    if (base) {
        controller = $.extend(this,base);
    }

    // Add actions

    $.extend(this,actions);

    // Set what's sent

    this.it = {};
    this.application = application;
    this.name = name;

}

// Use as constructor

DoTRoute.Controller.prototype.constructor = DoTRoute.Controller;

// Route

DoTRoute.Route = function(application,name,path,template,controller,enter,exit) {

    // Just use what's sent

    this.application = application;
    this.name = name;
    this.path = path;
    this.template = template;
    this.controller = controller;
    this.enter = enter;
    this.exit = exit;

    // Initialize patterns

    this.patterns = [];

    // Split up the path sent by / and iterate through 

    var paths = path.split('/').slice(1);
    for (var index = 0; index < paths.length; index++) {

        var pattern = {};

        // If we're surrounded by {}'s and have something in between, then we're a parameter

        if (paths[index].length > 2 && '{' == paths[index][0] && paths[index].slice(-1) == '}') {

            // Split everything between the {}'s by semi colon

            var parameter_regex = paths[index].slice(1,-1).split(':');

            // Grab the first piece 

            var parameter = parameter_regex.shift();

            // If there's a non-blank, that's the parameter name

            if (parameter) {
                pattern.parameter = parameter;
            }

            // If we have one more piece, that's a regex to match by, 
            // if two more, regex with options

            if (parameter_regex.length == 1) {
                pattern.regex = new RegExp(parameter_regex[0]);
            } else if (parameter_regex.length == 2) {
                pattern.regex = new RegExp(parameter_regex[0],parameter_regex[1]);
            }

        // No bounding curls, just exact match

        } else {
            pattern.exact = paths[index];
        }

        // Add this pattern to the patterns for the route

        this.patterns.push(pattern);

    }

}

// Use as constructor

DoTRoute.Route.prototype.constructor = DoTRoute.Route;

// Application

DoTRoute.Application = function(target,pane,wait) {

    // Initialize the crap out of everything

    this.routes = {};
    this.routing = [];
    this.partials = {};
    this.templates = {};
    this.controllers = {};

    this.current = {
        paths: null,
        controller: null,
        route: null,
        path: null,
        query: null
    };

    // No target sent, assume the body tag

    this.target = target ? target : "body";

    // No pane, sent, assume this page's window

    this.pane = pane ? pane : window;

    // No wait, just start

    if (!wait) {
        this.start();
    }

}

// Use as constructor

DoTRoute.Application.prototype.constructor = DoTRoute.Application;

// start - Start listening for events

DoTRoute.Application.prototype.start = function() {

    // Proxy like no one is watching

    $(this.pane).on('hashchange',$.proxy(this.router,this));  
    $(this.pane).on('load',$.proxy(this.router,this));  
    $(this.pane).on('unload',$.proxy(this.last,this));  

}

// partial - Map an uncompiled template to a name

DoTRoute.Application.prototype.partial = function(name,text) {

    // Map this by name

    this.partials[name] = text;

    return this.partials[name];

}

// template - Map a compiled template to a name

DoTRoute.Application.prototype.template = function(name,text,custom,data) {

    // Try to compile and map by name if successful. 
    // If it fails, let the user know which
    // template borked

    try {
        this.templates[name] = doT.template(text,custom,data);
    }
    catch (exception) {
        throw new DoTRoute.Exception("Failed to compile " + name + ": " + exception);
    }

    return this.templates[name];

}

// controller - Map a controller to a name

DoTRoute.Application.prototype.controller = function(name,base,actions) {

    // Lookup the base controller if it's a string and found

    base = typeof(base) == "string" && base in this.controllers ? this.controllers[base] : base;

    // Create using what's sent

    this.controllers[name] = new DoTRoute.Controller(this,name,base,actions);

    return this.controllers[name];

}

// route - Map a pattern to a callable entity

DoTRoute.Application.prototype.route = function(name,path,template,controller,enter,exit) {

    // Lookup template and controller by name if string and found

    template = typeof(template) == "string" && template in this.templates ? this.templates[template] : template;
    controller = typeof(controller) == "string" && controller in this.controllers ? this.controllers[controller] : controller;

    // If enter's a string and in the controller, proxy that,
    // else use what they sent, else just do a simple render

    if (typeof(enter) == "string" && enter in controller) {
        enter = $.proxy(controller[enter],controller);
    } else {
        enter = enter ? enter : function () {this.application.render()};
    }

    // If enter's a string and in the controller, proxy that,
    // else use what they sent, else just do a simple nothing

    if (typeof(exit) == "string" && exit in controller) {
        exit = $.proxy(controller[exit],controller);
    } else {
        exit = exit ? exit : function () {};
    }

    // Map by name and store to a list so that it can be search
    // in the order it was registered

    this.routes[name] = new DoTRoute.Route(this,name,path,template,controller,enter,exit);
    this.routing.push(name);

    return this.routes[name];

}

// match - Find a matching route

DoTRoute.Application.prototype.match = function(path) {

    // Split off the query part first, split paths by '/'
    // and initialize the current query

    var path_query = path.split('?');
    var paths = path_query.shift().split('/').slice(1);
    var query = {};
    
    // If there's something in the query, split each argument
    // and store decoded value to the argument name in the 
    // query object

    if (path_query.length) {
        $.each(path_query[0].split('&'),function(index,parameter) {
            var name_value = parameter.split('=');
            query[name_value[0]] = name_value.length > 1 ? decodeURIComponent(name_value[1]) : null;
        });
    }

    // Go through all the routes in the order they were added

    route_loop: for (var route_index = 0; route_index < this.routing.length; route_index++) {

        // Get the route 

        var route = this.routes[this.routing[route_index]];
        var path = {};

        // Lengths aren't the same, can't be a match

        if (paths.length != route.patterns.length) {
            continue route_loop;
        }

        // Loop over the route patterns because we know the lengths the 
        // same as paths

        for (var pattern_index = 0; pattern_index < route.patterns.length; pattern_index++) {

            var pattern = route.patterns[pattern_index];

            // If we're looking for an exact match and it ain't, or we're looking 
            // regex match and it doesn't, can't be a match

            if (("exact" in pattern && pattern.exact != paths[pattern_index]) ||
                ("regex" in pattern && !pattern.regex.test(paths[pattern_index]))) {
                continue route_loop;
            }

            // Whatever requirements we had are fulfilled at this point.  If there's 
            // a parameter to grab, use it. 

            if ("parameter" in pattern) {
                path[pattern.parameter] = paths[pattern_index];
            }

        }

        // If we're here, we match everyting.  Store what we
        // have to what's current and blow this pop stand.

        this.current.paths = paths;
        this.current.controller = route.controller;
        this.current.route = route;
        this.current.path = path;
        this.current.query = query;

        return true;

    }

    // We've failed if we've coem this far.  How sad.

    return false;

}

// last - check last route 

DoTRoute.Application.prototype.last = function() {

    // If we have a current route set,
    // call its ext function

    if (this.current.route) {
        this.current.route.exit(this);
    }

}

// router - match route and call

DoTRoute.Application.prototype.router = function() {

    // Get the current hash, and assume root if nada

    var hash = this.pane.location.hash;
    var path = (hash.slice(1) || "/");

    // Make sure we call the last route's exit function

    this.last();

    // Initialize current so if we fail we don't
    // have hangers on

    this.current = {
        paths: null,
        controller: null,
        route: null,
        path: null,
        query: null
    };

    // If we don't match nothing, bork

    if (!this.match(path)) {
        throw new DoTRoute.Exception("Unable to route: " + hash);
    }

    // Call the current route's enter function

    this.current.route.enter(this);

}

// link - Link to a route

DoTRoute.Application.prototype.link = function(route) {

    // Lookup by string.  Bork if not found.

    if (typeof(route) == "string") {

        if (!(route in this.routes)) {
            throw new DoTRoute.Exception("Can't find route: " + route);
        }

        route = this.routes[route];
    }

    // Go through all the paths in the route.  If it's an exact
    // match pattern, use that exactly.  Else use the next argument
    // sent.

    var paths = [];
    var argument = 1;
    for (var index = 0; index < route.patterns.length; index++) {
        paths.push("exact" in route.patterns[index] ? route.patterns[index].exact : arguments[argument++]);
    }

    var link = "#/" + paths.join("/")

    // If there's still an argument, then it's parameters

    if (argument < arguments.length) {
        link += "?" + $.param(arguments[argument]);
    }
    
    // Return it all pretty

    return link;

}

// go - Jump to a route

DoTRoute.Application.prototype.go = function(route) {

    // Use the route if it's already a hash, else call link
    // and use that

    this.pane.location.hash = typeof(route) == "string" && route[0] == '#' ? route : this.link.apply(this,arguments);
    //this.router();

}

// at - Determine if at a route, including parameters

DoTRoute.Application.prototype.at = function(route) {

    // If we're not at a route, then nope

    if (!this.current.route) {
        return false;
    }

    // Lookup by string.

    if (typeof(route) == "string" && route in this.routes) {
        route = this.routes[route];
    }

    // Return if not matching current

    if (route != this.current.route) {
        return false;
    }

    // Go through all the paths in the route.  Check wildcards if sent. 

    var argument = 0;
    for (var index = 0; index < route.patterns.length; index++) {
        if (!("exact" in route.patterns[index])) {
            if (arguments[++argument] != null && arguments[argument] != this.current.paths[index]) {
                return false;
            }
        }
    }

    // If we're here, everything lined up

    return true;

}

// refresh - Just reload the route

DoTRoute.Application.prototype.refresh = function() {

    // Great talk

    this.router();

}

// render - Apply to current data

DoTRoute.Application.prototype.render = function(it,template,target,pane) {

    // No template?  No problem!  Assume current route's

    if (!template) {
        template = this.current.route.template;
    } else {
        template = typeof(template) == "string" && template in this.templates ? this.templates[template] : template;
    }

    // No target?  No problem!  Assume app's

    if (!target) {
        target = this.target;
    }

    // No pane?  No problem!  Assume app's

    if (!pane) {
        pane = this.pane;
    }

    // In our app's window, set the jQuery target's 
    // html to whatever the template function returns
    // using the data that was sent to us

    $(target,pane.document).html(template(it));

}

