// Routes for the view
exports.view  = function view(req, res){
	console.log('view')
	res.render('view', {user: req.user});
}

// Error page if someone tries to access the view page
// without a proper query
exports.queryError  = function queryError(req, res){
	console.log('query-error')
	res.render('query-error', {user: req.user});
}

