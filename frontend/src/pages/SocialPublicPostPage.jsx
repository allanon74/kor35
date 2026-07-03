import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { socialGetPublicPostBySlug, resolveMediaUrl } from '../api';
import InstafameMediaCarousel from '../components/InstafameMediaCarousel';
import { formatCount } from '../utils/formatCount';

export default function SocialPublicPostPage() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await socialGetPublicPostBySlug(slug);
        if (mounted) setPost(data);
      } catch (e) {
        if (mounted) setError('Post non trovato o non pubblico.');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [slug]);

  if (loading) return <div className="p-8 text-center text-gray-500">Caricamento post...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!post) return null;

  const postImages =
    Array.isArray(post.immagini) && post.immagini.length > 0
      ? post.immagini
      : post.immagine
        ? [post.immagine]
        : [];

  const hasMedia = postImages.length > 0 || Boolean(post.video);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto p-4 md:p-8">
        <div
          className={`bg-white rounded-xl shadow border border-gray-200 overflow-hidden ${
            hasMedia ? 'flex flex-col lg:block lg:overflow-hidden' : 'max-w-2xl mx-auto'
          }`}
        >
          {hasMedia && (
            <div className="px-5 pt-5 pb-3 lg:hidden">
              <p className="text-sm text-gray-500">
                <span className="font-semibold text-gray-900">{post.autore_nome}</span>
                {' · '}
                {new Date(post.created_at).toLocaleString('it-IT')}
              </p>
            </div>
          )}

          {(postImages.length > 0 || post.video) && (
            <div className="order-2 lg:order-none lg:float-left lg:w-1/2 lg:max-w-[50%] lg:flex lg:items-center lg:justify-center lg:bg-black lg:min-h-[360px] lg:max-h-[720px] lg:border-r lg:border-gray-200">
              {postImages.length > 0 ? (
                <InstafameMediaCarousel images={postImages} alt={post.titolo} fullWidth className="border-gray-200" />
              ) : (
                <div className="w-full aspect-4/5 overflow-hidden border-y border-gray-200 bg-black lg:aspect-auto lg:h-full lg:max-h-[720px] lg:border-y-0">
                  <video controls src={resolveMediaUrl(post.video)} className="h-full w-full object-cover lg:object-contain" />
                </div>
              )}
            </div>
          )}

          {hasMedia && (
            <div className="hidden lg:block order-1 lg:order-none lg:overflow-hidden px-5 pt-5 pb-3 border-b border-gray-200">
              <p className="text-sm text-gray-500">
                <span className="font-semibold text-gray-900">{post.autore_nome}</span>
                {' · '}
                {new Date(post.created_at).toLocaleString('it-IT')}
              </p>
            </div>
          )}

          {!hasMedia && (
            <div className="px-5 pt-5 pb-3">
              <p className="text-sm text-gray-500">
                <span className="font-semibold text-gray-900">{post.autore_nome}</span>
                {' · '}
                {new Date(post.created_at).toLocaleString('it-IT')}
              </p>
            </div>
          )}

          {post.titolo && (
            <h1
              className={`px-5 pt-4 text-xl md:text-2xl font-bold text-gray-900 ${
                hasMedia ? 'order-3 lg:order-none' : ''
              }`}
            >
              {post.titolo}
            </h1>
          )}
          {post.testo && (
            <p
              className={`px-5 py-4 text-gray-800 whitespace-pre-wrap ${
                hasMedia ? 'order-3 lg:order-none' : ''
              }`}
            >
              {post.testo}
            </p>
          )}

          <div
            className={`px-5 py-4 text-sm text-gray-600 border-t border-gray-200 ${
              hasMedia ? 'order-4 lg:order-none lg:clear-both' : ''
            }`}
          >
            Like: <span className="font-semibold">{formatCount(post.likes_count)}</span> · Commenti:{' '}
            <span className="font-semibold">{formatCount(post.comments_count)}</span>
          </div>
        </div>

        <div className="mt-4 text-center">
          <Link to="/app/social" className="text-indigo-600 hover:text-indigo-500 font-semibold">
            Apri InstaFame
          </Link>
        </div>
      </div>
    </div>
  );
}
