#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import optparse
import json
import os
import gzip
import json

import MySQLdb

from seocrawler import crawl
from seoreporter import report


def run(options):
    if options.database:
        with open(options.database, 'r') as f:
            env = yaml.load(f)
        db_conf = env.get('db', {})
    else:
        db_conf = {
            'host': os.environ.get('SEO_DB_HOSTNAME'),
            'user': os.environ.get('SEO_DB_USERNAME'),
            'pass': os.environ.get('SEO_DB_PASSWORD'),
            'name': os.environ.get('SEO_DB_DATABASE'),
        }

    # Initialize the database cursor
    db = MySQLdb.connect(host=db_conf.get('host'), user=db_conf.get('user'),
        passwd=db_conf.get('pass'), db=db_conf.get('name'), use_unicode=True)

    urls = []
    url_associations = {}
    processed_urls = {}
    run_id = None
    if options.file:
        with open(options.file, 'r') as f:
            urls = [url.strip() for url in f.readlines()]
    elif options.base_url:
        urls = [options.base_url,]
    elif options.yaml:
        with open(options.yaml, 'r') as f:
            url_yaml = yaml.load(f)
            urls = url_yaml.get('seocrawlerurls', [])
    elif options.run_id:
        save_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'seocrawler', 'jobs', options.run_id + '.gz')
        if not os.path.exists(save_file):
            raise Exception('Save directory %s was not found' % save_file)

        with gzip.open(save_file, 'r') as f:
            content = f.read()
            data = json.loads(content)

        if not data:
            raise Exception('No save data found')

        urls = data.get('urls', [])
        url_associations = data.get('associations', {})


        cur = db.cursor()
        run_id = options.run_id

        cur.execute('SELECT id, address FROM crawl_urls WHERE run_id = %s',
            (options.run_id,))
        processed_urls = dict([(row[1], row[0]) for row in cur.fetchall()])

    run_id = crawl(urls, db, options.internal, options.delay,
        options.user_agent, url_associations, run_id, processed_urls, limit=options.limit)

    if options.output:
        with open(options.output, 'w') as f:
            f.write(report(db, 'build', 'junit', run_id))


if __name__ == "__main__":
    parser = optparse.OptionParser(description='Crawl the given url(s) and check them for SEO or navigation problems.')

    # Input sources
    inputs = optparse.OptionGroup(parser, "Input Options")

    inputs.add_option('-f', '--file', type="string",
        help='A file containing a list of urls (one url per line) to process.')
    inputs.add_option('-u', '--base_url', type="string",
        help='A single url to use as a starting point for crawling.')
    inputs.add_option('-r', '--run_id', type="string",
        help='The id from a previous run to resume.')
    inputs.add_option('-y', '--yaml', type="string",
        help='A yaml file containing a list of urls to process. The yaml file should have a section labeled "seocrawlerurls" that contains a list of the urls to crawl.')
    parser.add_option_group(inputs)

    # Processing options
    parser.add_option('-i', '--internal', action="store_true",
        help='Crawl any internal link urls that are found in the content of the page.')
    parser.add_option('-l', '--limit', action="store", type="int", default=0,
        help='The maximum number of internal links that will be followed.')
    parser.add_option('--user-agent', type="string", default='Screaming Frog SEO Spider/2.30',
        help='The user-agent string to request pages with.')
    parser.add_option('--delay', type="int", default=0,
        help='The number of milliseconds to delay between each request.')

    parser.add_option('--database', type="string",
        help='A yaml configuration file with the database configuration properties.')


    parser.add_option('-o', '--output', type="string",
        help='The path of the file where the output junit xml will be written to.')

    args = parser.parse_args()[0]

    run(args)
