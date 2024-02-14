#!/usr/bin/python
#
# test.py - SPARQL Protocol Test Suite
#

import os, sys, string, getopt
import RDF, SimpleRDF, Vocabulary
import sparqlclient, sparqlprottests
import rdfdiff
import httplib
import unittest

from sparqlprottests import *
from StringIO import StringIO

RDF.debug(0)
SimpleRDF.debug(0)

def usage():
    print """
Usage: %s [OPTIONS]

Standard arguments:

    -d, --data      Directory containing test manifest.ttl files.
    -s, --service   Execute query at given service.
    -h, --help      Display this help message.

Examples:

    python test.py -s http://sparql.org/sparql

        """ % sys.argv[:1].pop()

def main():

    data = "../data"
    verbose = False
    svc_hostport = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hds:", ["data", "service=", "help"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ('-d', '--data'):
            data = arg
        elif opt in ('-s', '--service'):
            svc_hostport = arg
        
    suite = unittest.TestSuite()
      
    map(lambda x: suite.addTest(SPARQLProtocolTestStub(x)), \
      sparqlprottests.load_tests(os.path.abspath(data), svc_hostport))

    unittest.TextTestRunner(verbosity=2,descriptions=1).run(suite)

class SPARQLProtocolTestStub(unittest.TestCase):
    def __init__(self, ptest):
        unittest.TestCase.__init__(self)
        self.ptest = ptest
    
    def shortDescription(self):
        return str(self.ptest["name"])
    
    def runTest(self):
      
        if self.ptest.get_service() is None:
           self.fail("expected a service property on manifest item")

        client = sparqlclient.SPARQLClient(self.ptest.get_service())
        client.set_query(self.ptest.get_query())
        #client.add_accept(entry.get_accept_types())
    
        ds = self.ptest.get_dataset();
    
        if ds:
            map(client.add_backgroundgraph, [ g["data"] for g in ds.get_defaultgraphs() ] )
            map(client.add_namedgraph, [ g["data"] for g in ds.get_namedgraphs() ] )
    
        result = client.execute()

        failures = []
       
        for expected in self.ptest.get_results():

            try:
                print client.get_responsecode()
                self.failUnlessEqual(int(str(expected["resultcode"])), client.get_responsecode(), "Response codes did not match.")
    
                if str(expected["resultContentType"]) in ("text/html"):
                    """ We do not worry about comparing things returned as html """
                    continue
    
                # I'm not sure what other response code other than 200
                # should I proceed on comparing result graphs.

                if client.get_responsecode() == 200:
                    p = None
                    q = None

                    if str(expected["resultContentType"]) in ("application/sparql-results+xml"):
                        p = sparql2graph(StringIO(expected.get_result())).to_string(name="ntriples")
                    else:
                        p = expected.get_result_as_model().to_string(name="ntriples")
        
                    if client.get_contenttype() in ("application/sparql-results+xml", "application/xml"):
                        q = sparql2graph(StringIO(result)).to_string(name="ntriples")

                        import urllib
                        params = urllib.urlencode({'xslfile': 'http://sparql.org/xml-to-html.xsl', 'xmlfile': client.get_requesturl()})
                        f = urllib.urlopen("http://www.w3.org/2005/08/online_xslt/xslt?%s" % params)
                        fw = open("%s.html" % (self.shortDescription()), "w")
                        fw.write(f.read())
                        fw.close()
                        f.close()

                    else:
                        q = SimpleRDF.load_model_from_string(result).to_string(name="ntriples")

                    self.failIf(not rdfdiff.compare_from_string(p, q), "ResultGraph did not match.")
                
            except Exception, e:
                  
                  failures.append(e)
        
            if len(failures) == 0:
                return
    
        # we have failure
        raise failures.pop()

if __name__ == '__main__':
    main()
  
