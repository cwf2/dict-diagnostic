#!/usr/bin/env perl

=head1 NAME

transliterate.pl - create a greek-latin transliteration dictionary

=head1 SYNOPSIS

transliterate.pl [options]

=head1 DESCRIPTION

Look for correspondences between the Greek stem list and the Latin list
based on simple transliteration rules. Print out a list of these that
can be used as a supplement to the translation dictionary.

=head1 OPTIONS AND ARGUMENTS

=over

=item --grc I<FILE>
Greek stem list to use; default is for the full corpus 
(F<data/common/grc.stem.freq>).

=item --la I<FILE>
Latin stem list to use; default is for the full corpus 
(F<data/common/la.stem.freq>).

=item B<--help>

Print usage and exit.

=item B<--quiet>

Don't print debugging messages to stderr.

=back

=head1 KNOWN BUGS

=head1 SEE ALSO

=head1 COPYRIGHT

University at Buffalo Public License Version 1.0.
The contents of this file are subject to the University at Buffalo Public License Version 1.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://tesserae.caset.buffalo.edu/license.txt.

Software distributed under the License is distributed on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for the specific language governing rights and limitations under the License.

The Original Code is transliterate.pl.

The Initial Developer of the Original Code is Research Foundation of State University of New York, on behalf of University at Buffalo.

Portions created by the Initial Developer are Copyright (C) 2007 Research Foundation of State University of New York, on behalf of University at Buffalo. All Rights Reserved.

Contributor(s): Chris Forstall <cforstall@gmail.com>

Alternatively, the contents of this file may be used under the terms of either the GNU General Public License Version 2 (the "GPL"), or the GNU Lesser General Public License Version 2.1 (the "LGPL"), in which case the provisions of the GPL or the LGPL are applicable instead of those above. If you wish to allow use of your version of this file only under the terms of either the GPL or the LGPL, and not to allow others to use your version of this file under the terms of the UBPL, indicate your decision by deleting the provisions above and replace them with the notice and other provisions required by the GPL or the LGPL. If you do not delete the provisions above, a recipient may use your version of this file under the terms of any one of the UBPL, the GPL or the LGPL.

=cut

use strict;
use warnings;

#
# Read configuration file
#

# modules necessary to read config file

use Cwd qw/abs_path/;
use File::Spec::Functions;
use FindBin qw/$Bin/;

# read config before executing anything else

my $lib;

BEGIN {

	# look for configuration file
	
	$lib = $Bin;
	
	my $oldlib = $lib;
	
	my $pointer;
			
	while (1) {

		$pointer = catfile($lib, '.tesserae.conf');
	
		if (-r $pointer) {
		
			open (FH, $pointer) or die "can't open $pointer: $!";
			
			$lib = <FH>;
			
			chomp $lib;
			
			last;
		}
									
		$lib = abs_path(catdir($lib, '..'));
		
		if (-d $lib and $lib ne $oldlib) {
		
			$oldlib = $lib;			
			
			next;
		}
		
		die "can't find .tesserae.conf!\n";
	}
	
	$lib = catdir($lib, 'TessPerl');
}

# load Tesserae-specific modules

use lib $lib;
use Tesserae;
use EasyProgressBar;

# modules to read cmd-line options and print usage

use Getopt::Long;
use Pod::Usage;

# load additional modules necessary for this script

use utf8;

# initialize some variables

my $help = 0;
my $quiet = 0;
my $file_grc = catfile($fs{data}, "common", "grc.stem.freq");
my $file_la = catfile($fs{data}, "common", "la.stem.freq");
my $show_scores;

# get user options

GetOptions(
    'grc=s' => \$file_grc,
    'la=s' => \$file_la,
    'scores' => \$show_scores,
	'help' => \$help,
    'quiet' => \$quiet
);

# print usage if the user needs help
if ($help) {

	pod2usage(1);
}

binmode STDOUT, ":utf8";

# load lists

print STDERR "Reading Greek: $file_grc..." unless $quiet;
my %greek = %{Tesserae::stoplist_hash($file_grc)};
print STDERR scalar(keys %greek) . " stems\n" unless $quiet;

print STDERR "Reading Latin: $file_la..." unless $quiet;
my %latin = %{Tesserae::stoplist_hash($file_la)};
print STDERR scalar(keys %latin) . " stems\n" unless $quiet;

# make a stoplist of the top 10 greek words

my @stop = sort {$greek{$b} <=> $greek{$a}} keys %greek;
@stop = @stop[0..9];

for (@stop) {
    delete $greek{$_};
}

# try it out

my $pr = ProgressBar->new(scalar(keys %greek), $quiet);

for my $g (sort keys %greek) {
    my @results = transliterate($g);
    
    @results = grep {exists $latin{$_}} @results;
    @results = grep {length($_) > 3} @results;
    
    for my $l (@results) {
        my @row = ($g,$l);
        if ($show_scores) {
            push @row, ($greek{$g}, $latin{$l});
        }
        print join(",", @row);
        print "\n";
    }
    $pr->advance;
}
$pr->finish;

#
# subroutines
#

sub transliterate {
    my $s = shift;
    
    # rough breathing
    if ($s =~ /\x{0314}/) { $s = "h" . $s }
    
    # strip all other accents
    $s =~ s/[^[:alpha:]]//g;
    
    # now exchange characters
    for ($s) {
        #2nd decl nominative endings
        s/ος$/Os/;
        s/ον$/On/;
        s/οι$/i/;
        # diphthongs
        s/αι/ae/g;
        s/ει/E/g;
        s/οι/oe/g;
        # double consonants
        s/θ/th/g;
        s/φ/ph/g;
        s/χ/ch/g;
        s/ψ/ps/g;
        # single letters        
        tr/αβγδεζηικλμνξοπρσςτυω/abgdezHiKlmnxoprsstYo/;
    }
    
    $s =~ s/hr/rh/;
    
    # allow multiple guesses in case of ambiguous letters
    my @results = ambiguities($s);
    
    return @results;
}

sub ambiguities {
    my @s = @_;
    my @results;
    
    for my $s (@s) {
        if ($s =~ /H/) {
            my ($r1, $r2) = ($s) x 2;
            $r1 =~ s/H/e/;
            $r2 =~ s/H/a/;
            push @results, ambiguities($r1, $r2);
        } elsif ($s =~ /E/) {
            my ($r1, $r2) = ($s) x 2;
            $r1 =~ s/E/ei/;
            $r2 =~ s/E/e/;
            push @results, ambiguities($r1, $r2);
        } elsif ($s =~ /K/) {
            my ($r1, $r2) = ($s) x 2;
            $r1 =~ s/K/k/;
            $r2 =~ s/K/c/;
            push @results, ambiguities($r1, $r2);
        } elsif ($s =~ /Y/) {
            my ($r1, $r2) = ($s) x 2;
            $r1 =~ s/Y/u/;
            $r2 =~ s/Y/y/;
            push @results, ambiguities($r1, $r2);
        } elsif ($s =~ /O/) {
            my ($r1, $r2) = ($s) x 2;
            $r1 =~ s/O/u/;
            $r2 =~ s/O/o/;
            push @results, ambiguities($r1, $r2);
        } else {
            push @results, $s;
        }
    }
    
    return @results;
}