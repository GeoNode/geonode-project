var gulp = require('gulp');
var gutil = require('gulp-util');
var pkg = require('./package.json');
var concat = require('gulp-concat');
var less = require('gulp-less');
var del = require('del');

gulp.task('clean:site_base.css', [], function () {
  return del([ './css/site_base.css' ]);
});

gulp.task('compile:site_base.css', [], function() {
  return gulp.src(["./less/site_base.less"], {base: './'})
    .pipe(less({}))
    .pipe(concat("site_base.css"))
    .pipe(gulp.dest("./css"));
});

gulp.task('watch', function() {
  gulp.watch("./less/**/*", ['clean:site_base.css', 'compile:site_base.css']);
});

gulp.task('default', ['watch', 'clean:site_base.css', 'compile:site_base.css']);
